﻿import datetime
import pytz
import time
import dateutil.parser
import dateutil.tz
import syslog
import os.path
import pprint
import xml.etree.ElementTree as ET
import json

try:
    import http.client as httplib #python3+
except:
    import httplib      #python2

try:
    from urllib.request import Request, urlopen #python3+
except ImportError:
    from urllib2 import Request, urlopen        #python2

try:
    from urllib.parse import urlparse   #python3+
except ImportError:
    from urlparse import urlparse

import weewx.units
import weeutil.weeutil
from weewx.cheetahgenerator import SearchList

#feeslike lookups
DaySummerCoastRanges = { -40: 'Cold', 16: 'Cool', 22: 'Mild', 27: 'Warm', 32: 'Hot', 37: 'Very Hot' }
DaySummerInlandPlains = { -40: 'Cold', 20: 'Cool', 25: 'Mild', 30: 'Warm', 35: 'Hot', 40: 'Very Hot' }
DaySummerTropics = { -40: '-', 35: 'Hot', 40: '-' }

NightSummerSouthRanges = { -40: 'Cold', 10: 'Cool', 15: 'Mild', 18: 'Warm', 22: 'Hot' }
NightSummerNorth = { -40: 'Cold', 13: 'Cool', 18: 'Mild', 21: 'Warm', 25: 'Hot' }
NightSummerTropics = {  -40: 'Cool', 20: '-' }

DayWinterSouthRanges = { -40: 'Very Cold', 10: 'Cold', 13: 'Cool', 16: 'Mild', 20: 'Warm' }
DayWinterNorth = { -40: 'Very Cold', 10: 'Cold', 15: 'Cool', 20: 'Mild', 25: 'Warm' }
DayWinterTropics = { -40: 'Cold', 20: 'Cool', 26: '-' }

NightWinterSouthRanges = { -40: 'Very Cold', 1: 'Cold', 5: 'Cool', 10: 'Mild' }
NightWinterNorth = { -40: 'Very Cold', 5: 'Cold', 10: 'Cool', 15: 'Mild' }
NightWinterTropics = { -40: 'Cold', 13: 'Cool', 18: '-' }

requestHeadersDefault = {
                        'Connection': 'keep-alive',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'
}

feelslikeDict = {
                'DaySummerCoastRanges': DaySummerCoastRanges,
                'DaySummerInlandPlains': DaySummerInlandPlains,
                'DaySummerTropics': DaySummerTropics,
                'NightSummerSouthRanges': NightSummerSouthRanges,
                'NightSummerNorth': NightSummerNorth,
                'NightSummerTropics': NightSummerTropics,
                'DayWinterSouthRanges': DayWinterSouthRanges,
                'DayWinterNorth': DayWinterNorth,
                'DayWinterTropics': DayWinterTropics,
                'NightWinterSouthRanges': NightWinterSouthRanges,
                'NightWinterNorth': NightWinterNorth,
                'NightWinterTropics': NightWinterTropics
                }

feelslikeLocalDefaults = ['DaySummerCoastRanges', 'NightSummerSouthRanges', 'DayWinterSouthRanges', 'NightWinterSouthRanges']

iconsDefault = { 
                        '1' : 'http://www.bom.gov.au/images/symbols/large/sunny.png', 
                        '2' : 'http://www.bom.gov.au/images/symbols/large/clear.png', 
                        '3' : 'http://www.bom.gov.au/images/symbols/large/partly-cloudy.png',
                        '4' : 'http://www.bom.gov.au/images/symbols/large/cloudy.png',
                        '5' : '',
                        '6' : 'http://www.bom.gov.au/images/symbols/large/haze.png',
                        '7' : '',
                        '8' : 'http://www.bom.gov.au/images/symbols/large/light-rain.png',
                        '9' : 'http://www.bom.gov.au/images/symbols/large/wind.png',
                        '10' : 'http://www.bom.gov.au/images/symbols/large/fog.png',
                        '11' : 'http://www.bom.gov.au/images/symbols/large/showers.png',
                        '12' : 'http://www.bom.gov.au/images/symbols/large/rain.png',
                        '13' : 'http://www.bom.gov.au/images/symbols/large/dust.png',
                        '14' : 'http://www.bom.gov.au/images/symbols/large/frost.png',
                        '15' : 'http://www.bom.gov.au/images/symbols/large/snow.png',
                        '16' : 'http://www.bom.gov.au/images/symbols/large/storm.png',
                        '17' : 'http://www.bom.gov.au/images/symbols/large/light-showers.png',
                        '18' : 'http://www.bom.gov.au/images/symbols/large/heavy-showers.png' 
                    }
                    
iconsSmlDefault = { 
                        '1' : 'http://www.bom.gov.au/images/symbols/small/sunny.png', 
                        '2' : 'http://www.bom.gov.au/images/symbols/small/clear.png', 
                        '3' : 'http://www.bom.gov.au/images/symbols/small/partly-cloudy.png',
                        '4' : 'http://www.bom.gov.au/images/symbols/small/cloudy.png',
                        '5' : '',
                        '6' : 'http://www.bom.gov.au/images/symbols/small/haze.png',
                        '7' : '',
                        '8' : 'http://www.bom.gov.au/images/symbols/small/light-rain.png',
                        '9' : 'http://www.bom.gov.au/images/symbols/small/wind.png',
                        '10' : 'http://www.bom.gov.au/images/symbols/small/fog.png',
                        '11' : 'http://www.bom.gov.au/images/symbols/small/showers.png',
                        '12' : 'http://www.bom.gov.au/images/symbols/small/rain.png',
                        '13' : 'http://www.bom.gov.au/images/symbols/small/dust.png',
                        '14' : 'http://www.bom.gov.au/images/symbols/small/frost.png',
                        '15' : 'http://www.bom.gov.au/images/symbols/small/snow.png',
                        '16' : 'http://www.bom.gov.au/images/symbols/small/storm.png',
                        '17' : 'http://www.bom.gov.au/images/symbols/small/light-showers.png',
                        '18' : 'http://www.bom.gov.au/images/symbols/small/heavy-showers.png'  
                    }                            
                    
rainImgsDefault = { 
                        '0%' : 'http://www.bom.gov.au/images/ui/weather/rain_0.gif',
                        '5%' : 'http://www.bom.gov.au/images/ui/weather/rain_5.gif',
                        '10%' : 'http://www.bom.gov.au/images/ui/weather/rain_10.gif',
                        '20%' : 'http://www.bom.gov.au/images/ui/weather/rain_20.gif',
                        '30%' : 'http://www.bom.gov.au/images/ui/weather/rain_30.gif',
                        '40%' : 'http://www.bom.gov.au/images/ui/weather/rain_40.gif',
                        '50%' : 'http://www.bom.gov.au/images/ui/weather/rain_50.gif',
                        '60%' : 'http://www.bom.gov.au/images/ui/weather/rain_60.gif',
                        '70%' : 'http://www.bom.gov.au/images/ui/weather/rain_70.gif',
                        '80%' : 'http://www.bom.gov.au/images/ui/weather/rain_80.gif',
                        '90%' : 'http://www.bom.gov.au/images/ui/weather/rain_90.gif',
                        '95%' : 'http://www.bom.gov.au/images/ui/weather/rain_95.gif',
                        '100%' : 'http://www.bom.gov.au/images/ui/weather/rain_100.gif'
                    }     


class ausutils(SearchList):
    """Class that implements the '$aus' tag."""

    def __init__(self, generator):
        SearchList.__init__(self, generator)
        self.aus = { "feelslike" : self.feelslikeFunc }

        try:
            feelslikeLocalList = weeutil.weeutil.option_as_list(self.generator.skin_dict['AusSearch']['feelslike']['feelslikeLocal'])
        except KeyError:
            feelslikeLocalList = feelslikeLocalDefaults

        try:
            self.feelslikeLocal = {}

            self.feelslikeLocal['DaySummer']      = feelslikeDict[feelslikeLocalList[0]]
            self.feelslikeLocal['NightSummer']    = feelslikeDict[feelslikeLocalList[1]]
            self.feelslikeLocal['DayWinter']      = feelslikeDict[feelslikeLocalList[2]]
            self.feelslikeLocal['NightWinter']    = feelslikeDict[feelslikeLocalList[3]]

            syslog.syslog(syslog.LOG_DEBUG, "aussearch: feelslikeLocal['DaySummer'] = %s" % (pprint.pformat(self.feelslikeLocal['DaySummer'])))
            syslog.syslog(syslog.LOG_DEBUG, "aussearch: feelslikeLocal['NightSummer'] = %s" % (pprint.pformat(self.feelslikeLocal['NightSummer'])))
            syslog.syslog(syslog.LOG_DEBUG, "aussearch: feelslikeLocal['DayWinter'] = %s" % (pprint.pformat(self.feelslikeLocal['DayWinter'])))
            syslog.syslog(syslog.LOG_DEBUG, "aussearch: feelslikeLocal['NightWinter'] = %s" % (pprint.pformat(self.feelslikeLocal['NightWinter'])))
        except KeyError:
            syslog.syslog(syslog.LOG_ERR, "aussearch: invalid feelslikeLocal settings [%s, %s, %s, %s]" 
                          % feelslikeLocalList[0], feelslikeLocalList[1], feelslikeLocalList[2], feelslikeLocalList[3])

        try:
            self.iconsFolder = self.generator.skin_dict['AusSearch']['icons_folder']
        except KeyError:
            self.iconsFolder = '' 

        self.aus['icons'] = {}
        for iconX in range(1, 19):
            try:
                self.aus['icons'][str(iconX)] = self.iconsFolder + '/' + self.generator.skin_dict['AusSearch']['icons'][str(iconX)]
            except KeyError:
                self.aus['icons'][str(iconX)] = iconsDefault[str(iconX)]

        self.aus['iconsSml'] = {}
        for iconX in range(1, 19):
            try:
                self.aus['iconsSml'][str(iconX)] = self.iconsFolder + '/' + self.generator.skin_dict['AusSearch']['iconsSml'][str(iconX)]
            except KeyError:
                self.aus['iconsSml'][str(iconX)] = iconsSmlDefault[str(iconX)]

        self.aus['rainImgs'] = {}
        for rainImgsX in [0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]:
            try:
                self.aus['rainImgs'][str(rainImgsX)+'%'] = self.iconsFolder + '/' + self.generator.skin_dict['AusSearch']['rainImgs'][str(rainImgsX)]
            except KeyError:
                self.aus['rainImgs'][str(rainImgsX)+'%'] = rainImgsDefault[str(rainImgsX)+'%']

        try:
            self.cache_root = self.generator.skin_dict['AusSearch']['cache_root']
        except KeyError:
            self.cache_root = '/var/lib/weewx/aussearch'
        
        try:
            self.request_headers = self.generator.skin_dict['AusSearch']['request_headers']
        except KeyError:
            self.request_headers = requestHeadersDefault

        syslog.syslog(syslog.LOG_DEBUG, "aussearch: self.request_headers %s" % self.request_headers)

        try:
            self.staleness_time = float(self.generator.skin_dict['AusSearch']['staleness_time'])
        except KeyError:
            self.staleness_time = 15 * 60 #15 minutes

        try:
            self.refresh_time = float(self.generator.skin_dict['AusSearch']['refresh_time'])
        except KeyError:
            self.refresh_time = 30 * 60 #30 minutes
        
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
        
        try:
            xml_files = self.generator.skin_dict['AusSearch']['xml_files']
        except KeyError:
            xml_files = None
        
        if xml_files is not None:
            for xml_file in xml_files:
                self.aus[xml_file] = XmlFileHelper(self.generator.skin_dict['AusSearch']['xml_files'][xml_file],
                                                     self,
                                                     generator.formatter,
                                                     generator.converter)

        try:
            json_files = self.generator.skin_dict['AusSearch']['json_files']
        except KeyError:
            json_files = None

        if json_files is not None:
            for json_file in json_files:
                self.aus[json_file] = JsonFileHelper(self.generator.skin_dict['AusSearch']['json_files'][json_file],
                                                     self,
                                                     generator.formatter,
                                                     generator.converter)
    
        try:
            localization = self.generator.skin_dict['AusSearch']['local']
        except KeyError:
            localization = None

        if localization is not None:
            for localization_object in localization:
                try:
                    self.aus[localization_object] = \
                        self.aus[self.generator.skin_dict['AusSearch']['local'][localization_object]]
                except KeyError:
                    syslog.syslog(syslog.LOG_ERR, "aussearch: localization error for %s" % (localization_object))

        try:
            index_locality = self.generator.skin_dict['AusSearch']['localities']['index_locality']
        except KeyError:
            index_locality = 'Sydney'

        self.aus['index_locality'] = index_locality
  
    def get_extension_list(self, timespan, db_lookup):
        return [self]
    
    def feelslikeFunc(self, T_C=None, TS=None):
        if T_C is None or TS is None:
            return None
        try:
            DT = datetime.datetime.fromtimestamp(TS)
            if DT.month >= 10 or DT.month <= 3:
                # October to March - 'Summer'
                if DT.hour >= 9 and DT.hour < 21:
                    #Daytime
                    feelslikeLookup = self.feelslikeLocal['DaySummer'] 
                else:
                    #Nighttime
                    feelslikeLookup = self.feelslikeLocal['NightSummer']
            else:
                # April to September - 'Winter'
                if DT.hour >= 9 or DT.hour < 21:
                    #Daytime
                    feelslikeLookup = self.feelslikeLocal['DayWinter']
                else:
                    #Nighttime
                    feelslikeLookup = self.feelslikeLocal['NightWinter']        
            return feelslikeLookup[max(k for k in feelslikeLookup if k < T_C)]
        except:
            return "-"
                
class XmlFileHelper(object):
    """Helper class used for for the xml file template tag."""
    def __init__(self, xml_file, searcher, formatter, converter):
        """
        xml_file: xml file we are reading. <amoc><next-routine-issue-time-utc> used by default for staleness checking
        formatter: an instance of Formatter
        converter: an instance of Converter
        """

        self.xml_file = xml_file

        try:
            xml_file_path_parts = xml_file.split('/')
            xml_file_parts = xml_file_path_parts[-1].split('.')
        except ValueError as e:
            syslog.syslog(syslog.LOG_ERR, "aussearch: bad xml file format: %s: %s" % (xml_file, e.message))
            return

        self.local_file = xml_file_path_parts[-1]
        self.local_file_path = os.path.join(searcher.cache_root, self.local_file)
        self.is_ftp = True if xml_file_path_parts[0] == "ftp:" else False
        # Build remote amoc file path from remote xml file path
        # ftp://ftp.bom.gov.au/anon/gen/fwo/IDN11060.xml
        # => ftp://ftp.bom.gov.au/anon/gen/fwo/IDN11060.amoc.xml
        self.xml_file_amoc = '/'.join(
            [
                '/'.join(xml_file_path_parts[0:-1]),
                '.'.join([xml_file_parts[0], "amoc", xml_file_parts[-1]])
            ])

        if os.path.exists(self.local_file_path):
            try:
                self.dom = ET.parse(open(self.local_file_path, "r"))
                self.root = self.dom.getroot()
            except ET.ParseError as e:
                syslog.syslog(syslog.LOG_ERR, "aussearch: bad cache xml file %s: %s" % (self.local_file_path, e))
                self.root = None
                file_stale = True

            if self.root is not None:
                file_stale = False 

                nextIssue = self.root.find('amoc/next-routine-issue-time-utc')
                if nextIssue is not None:
                    check_datetime = dateutil.parser.parse(nextIssue.text) + \
                                     datetime.timedelta(seconds=searcher.staleness_time)
                    # For completeness we need to make sure that we are comparing timezone aware times
                    # since the parse of next-routine-issue-time-utc wil return a timezone aware time
                    # hence we pass a utc timezone to get the current utc time as a timezone aware time
                    # eg. datetime.datetime(2016, 12, 4, 0, 52, 34, tzinfo=tzutc())
                    now_datetime = datetime.datetime.now(dateutil.tz.tzutc())
                    syslog.syslog(syslog.LOG_DEBUG, "aussearch: check xml file: %s expires %s" %
                                  (self.local_file_path, check_datetime))
                    
                    if now_datetime >= check_datetime:
                        file_stale = True
                        syslog.syslog(syslog.LOG_DEBUG, "aussearch: xml file is stale: %s" % (self.local_file_path))
                else:
                    check_datetime = datetime.datetime.utcfromtimestamp(os.path.getmtime(self.local_file_path)) + \
                                     datetime.timedelta(seconds=searcher.staleness_time)
                    now_datetime = datetime.datetime.utcnow()
                    if now_datetime >= check_datetime:
                        file_stale = True

                # If not stale from cache information, check if amoc XML exists and check its sent time
                # Generally only ftp files have amoc check files
                if not file_stale and self.is_ftp:
                    syslog.syslog(syslog.LOG_DEBUG,
                                  "aussearch: xml: checking cache sent-time va remote amoc sent-time: %s" %
                                  (self.local_file))
                    try:
                        data = FileFetch.fetch(self.xml_file_amoc, searcher.request_headers, True)
                        amoc_dom = ET.fromstring(data)
                        sentTimeCache = self.root.find('amoc/sent-time').text
                        sentTimeAmoc = amoc_dom.find('sent-time').text
                        syslog.syslog(syslog.LOG_DEBUG,
                                      "aussearch: xml: %s: sent-time: %s" % (self.local_file_path, sentTimeCache))
                        syslog.syslog(syslog.LOG_DEBUG,
                                      "aussearch: xml: %s: sent-time: %s" % (self.xml_file_amoc, sentTimeAmoc))
                        if sentTimeAmoc != sentTimeCache:
                            syslog.syslog(syslog.LOG_DEBUG, "aussearch: xml file is stale: %s" %
                                          (self.local_file_path))
                            file_stale = True
                    except (AttributeError, IOError, ET.ParseError):
                        # Amoc file may not exist or parse well. That is fine, we just won't use
                        pass
            else:
                file_stale = True
        else:
            file_stale = True

        if file_stale:
            try:
                data = FileFetch.fetch(self.xml_file, searcher.request_headers, self.is_ftp)
                with open(self.local_file_path, 'w') as f:
                    f.write(data)
                    syslog.syslog(syslog.LOG_DEBUG, "aussearch: xml file downloaded: %s" % (self.xml_file))
                self.dom = ET.parse(open(self.local_file_path, "r"))
                self.root = self.dom.getroot()
            except IOError as e:
                syslog.syslog(syslog.LOG_ERR, "aussearch: cannot download xml file %s: %s" % (self.xml_file, e))
                self.root = None
        
        if self.root is not None:
            self.root_node = XMLNode(self.root)
    
    @property
    def xmlFile(self):
        """Return the xml_file we are using"""
        return self.xml_file
     
    def __getattr__(self, child_or_attrib):
        # This is to get around bugs in the Python version of Cheetah's namemapper:
        if child_or_attrib in ['__call__', 'has_key']:
            raise AttributeError
        
        if self.root_node is not None:
            return getattr(self.root_node, child_or_attrib)
        else:
            raise AttributeError

class XMLNode(object):
    def __init__(self, node):
        self.node = node
    
    def __call__(self, *args, **kwargs):
        return self.search(*args, **kwargs)
        
    def getNodes(self, tag=None):
        #TODO getNodes to support search and use node.findAll
        #For now this should do in getting all locations in a forecast
        nodes = self.node.iter(tag)

        xmlNodes = []
        for node in nodes:
            xmlNodes.append(XMLNode(node))

        return xmlNodes
    
    def getNode(self, *args, **kwargs):
        """
        Enables getting the current node.
        
        Useful for calls like 
        $aus.NSWMETRO.forecast('area',description="Parramatta").getNode('forecast_period',index="0").text
        """    
        return self.search(*args, **kwargs)
        
    def search(self, *args, **kwargs):
        """Lookup a node using a attribute pairs"""
        node_search = ""
           
        if len(args) == 0 and len(kwargs) == 0:
            #can't build a meaningful search string, return self
            return self
        elif len(args) == 1 and len(kwargs) == 0:
            #assume that caller is passing a full XMLPath search string
            node_search = args[0]
        else:
            node_search = "."
            for xArg in args:
                node_search += '/'
                node_search += xArg
                
            for key, value in kwargs.items():
                node_search += str.format("[@{0}='{1}']", key, value)
        
        childNode = self.node.find(node_search)
        return XMLNode(childNode) if childNode is not None else None
    
    def toString(self, addLabel=True, useThisFormat=None, NONE_string=None):
        #TODO: What to do here? We are not dealing with value tuples. YET!
        return self.node.text if self.node.text is not None else NONE_string
        
    def __str__(self):
        """Return as string"""
        return self.toString()
    
    @property
    def string(self, NONE_string=None):
        """Return as string with an optional user specified string to be
        used if None"""
        return self.toString(NONE_string=NONE_string)
    
    def __getattr__(self, child_or_attrib):
        child_or_attrib = child_or_attrib.replace("__", "-")
         
        #try to look up an attribute
        if ET.iselement(self.node):
            attrib = self.node.get(child_or_attrib)
        
        if attrib is not None:
            return attrib
        
        #try to find a child
        childNode = self.node.find(child_or_attrib)
        if childNode is not None:
            return XMLNode(childNode)
        else:
            raise AttributeError

class JsonFileHelper(object):
    """Helper class used for for the xml file template tag."""
    def __init__(self, json_file, searcher, formatter, converter):
        """
        json_file: xml file we are reading.
        formatter: an instance of Formatter
        converter: an instance of Converter
        """
        self.json_file = json_file
        self.local_file = json_file.split('/')[-1]
        self.local_file_path = os.path.join(searcher.cache_root, self.local_file)
 
        if os.path.exists(self.local_file_path):
            try:
                self.root = json.load(open(self.local_file_path, "r"))
            except (IOError, ValueError) as e:
                syslog.syslog(syslog.LOG_ERR, "aussearch: cannot load local json file %s: %s" % (self.local_file_path, e))
                self.root = None
                file_stale = True

            if self.root is not None:
                try:
                    latest_data_utc = self.root['observations']['data'][0]['aifstime_utc']
                except KeyError:
                    latest_data_utc = None

                if latest_data_utc is not None:
                    check_datetime = dateutil.parser.parse(latest_data_utc + "UTC") + \
                                     datetime.timedelta(seconds=searcher.refresh_time) + \
                                     datetime.timedelta(seconds=searcher.staleness_time)
                    # For completeness we need to make sure that we are comparing timezone aware times
                    # since the parse of next-routine-issue-time-utc wil return a timezone aware time
                    # hence we pass a utc timezone to get the current utc time as a timezone aware time
                    # eg. datetime.datetime(2016, 12, 4, 0, 52, 34, tzinfo=tzutc())
                    now_datetime = datetime.datetime.now(dateutil.tz.tzutc())
                    syslog.syslog(syslog.LOG_DEBUG, "aussearch: check json file: %s expires %s" %
                                  (self.local_file_path, check_datetime))

                    if now_datetime <= check_datetime:
                        file_stale = False
                    else:
                        file_stale = True
                        syslog.syslog(syslog.LOG_DEBUG, "aussearch: json file is stale: %s" % (self.local_file_path))
                else:
                    file_stale = True
                    syslog.syslog(syslog.LOG_DEBUG, "aussearch: json file bad data assuming stale: %s" %
                                  (self.local_file_path))
        else:
            file_stale = True
            syslog.syslog(syslog.LOG_DEBUG, "aussearch: json file does not exist: %s" %
                          (self.local_file_path))
        
        if file_stale:
            try:
                data = FileFetch.fetch(self.json_file, searcher.request_headers)
                with open(self.local_file_path, 'w') as f:
                    f.write(data)
                    syslog.syslog(syslog.LOG_DEBUG, "aussearch: json file downloaded: %s" % (self.json_file))
                self.root = json.load(open(self.local_file_path, "r"))
            except IOError as e:
                syslog.syslog(syslog.LOG_ERR, "aussearch: cannot download json file %s: %s" % (self.json_file, e))

        if self.root is not None:
            self.root_node = JSONNode(self.root)
    
    @property
    def jsonFile(self):
        """Return the json_file we are using"""
        return self.json_file
     
    def __getattr__(self, key_or_index):
        # This is to get around bugs in the Python version of Cheetah's namemapper:
        if key_or_index in ['__call__', 'has_key']:
            raise AttributeError
        
        if self.root_node is not None:
            return getattr(self.root_node, key_or_index)
        else:
            raise AttributeError

class JSONNode(object):
    def __init__(self, node):
        self.node = node
    
    def __call__(self, key_or_index):
        return self.walk(key_or_index)
          
    def walk(self, key_or_index):
        """Walk the json data"""
        childNode = None

        if isinstance(self.node, dict):
            try:
                childNode = self.node[key_or_index]
            except KeyError:
                raise AttributeError
        elif isinstance(self.node, list):
            try:
                index = int(key_or_index)
                childNode = self.node[index]
            except ValueError:
                pass
            except IndexError:
                raise AttributeError

            if childNode is None:
                try:
                    childNode = self.node[0][key_or_index]
                except KeyError:
                    raise AttributeError
        else:
            raise AttributeError

        return JSONNode(childNode) if childNode is not None else None
    
    def toString(self, addLabel=True, useThisFormat=None, NONE_string=None):
        #TODO: What to do here? We are not dealing with value tuples. YET!
        return str(self.node) if self.node is not None else NONE_string
        
    def __str__(self):
        """Return as string"""
        return self.toString()
    
    @property
    def string(self, NONE_string=None):
        """Return as string with an optional user specified string to be
        used if None"""
        return self.toString(NONE_string=NONE_string)
    
    def __getattr__(self, key_or_index):
        key_or_index = key_or_index.replace("__", "-")
         
        return self.walk(key_or_index)

class FileFetch(object):
    @staticmethod
    def fetch(url, headers, is_ftp=False):
        # Use urllib2 for FTP
        # Use http.client/httplib for all else as BOM needs to see header 'Connection: keep-alive' 
        # to believe we are a browser
        if (is_ftp):
            request = Request(url, headers)
            fp = urlopen(request)
            data = fp.read().decode()
            fp.close()
            return data
        else:
            parsedUrl = urlparse(url)
            connection = httplib.HTTPConnection(parsedUrl.netloc)
            connection.request('GET', parsedUrl.path, headers=headers)
            response = connection.getresponse()
            data = response.read().decode()
            return data
