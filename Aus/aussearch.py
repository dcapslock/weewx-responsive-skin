import datetime
import pytz
import time
import dateutil.parser
import dateutil.tz
import syslog
import os.path
import pprint
import xml.etree.cElementTree as ET

from urllib import urlopen

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
          
        self.aus['icons'] = { 
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
                            
        self.aus['iconsSml'] = { 
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
                            
        self.aus['rainImgs'] = { 
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
        
        try:
            self.cache_root = self.generator.skin_dict['AusSearch']['cache_root']
        except KeyError:
            self.cache_root = '/var/lib/weewx/aussearch'
        
        try:
            self.staleness_time = float(self.generator.skin_dict['AusSearch']['staleness_time'])
        except KeyError:
            self.staleness_time = 15 * 60 #15 minutes
        
        if not os.path.exists(self.cache_root):
            os.makedirs(self.cache_root)
        
        try:
            xml_files = self.generator.skin_dict['AusSearch']['xml_files']
        except:
            xml_files = None
        
        for xml_file in xml_files:
            self.aus[xml_file] = XmlFileHelper(self.generator.skin_dict['AusSearch']['xml_files'][xml_file],
                                                 self,
                                                 generator.formatter,
                                                 generator.converter)

        try:
            localization = self.generator.skin_dict['AusSearch']['local']
        except:
            localization = None

        for localization_object in localization:
            try:
                self.aus[localization_object] = self.aus[self.generator.skin_dict['AusSearch']['local'][localization_object]]
            except KeyError:
                syslog.syslog(syslog.LOG_ERR, "aussearch: localization error for %s" % (localization_object))

        try:
            index_locality = self.generator.skin_dict['AusSearch']['localities']['index_locality']
        except:
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
                if DT.hour >= 9 and DT.hour <= 21:
                    #Daytime
                    feelslikeLookup = self.feelslikeLocal['DaySummer'] 
                else:
                    #Nighttime
                    feelslikeLookup = self.feelslikeLocal['NightSummer']
            else:
                # April to September - 'Winter'
                if DT.hour >= 9 or DT.hour <= 21:
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
        self.local_file = xml_file.split('/')[-1]
        self.local_file_path = os.path.join(searcher.cache_root, self.local_file)
        
        if os.path.exists(self.local_file_path):
            self.dom = ET.parse(open(self.local_file_path, "r"))
            self.root = self.dom.getroot()
            file_stale = False 

            nextIssue = self.root.find('amoc/next-routine-issue-time-utc')
            if nextIssue is not None:
                check_datetime = dateutil.parser.parse(nextIssue.text) + datetime.timedelta(seconds=searcher.staleness_time)
                # For completeness we need to make sure that we are comparing timezone aware times
                # since the parse of next-routine-issue-time-utc wil return a timezone aware time
                # hence we pass a utc timezone to get the current utc time as a timezone aware time
                # eg. datetime.datetime(2016, 12, 4, 0, 52, 34, tzinfo=tzutc())
                now_datetime = datetime.datetime.now(dateutil.tz.tzutc())
                
                if now_datetime >= check_datetime:
                    file_stale = True
            else:
                check_datetime = datetime.datetime.utcfromtimestamp(os.path.getmtime(self.local_file_path)) + datetime.timedelta(seconds=searcher.staleness_time)
                now_datetime = datetime.datetime.utcnow()
                if now_datetime >= check_datetime:
                    file_stale = True
        else:
            file_stale = True

        if file_stale:
            try:
                data = urlopen(self.xml_file).read()
                with open(self.local_file_path, 'w') as f:
                    f.write(data)
                self.dom = ET.parse(open(self.local_file_path, "r"))
                self.root = self.dom.getroot()
            except IOError, e:
                syslog.syslog(syslog.LOG_ERR, "aussearch: cannot download xml file %s: %s" % (self.xml_file, e))
        
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
                
            for key, value in kwargs.iteritems():
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
