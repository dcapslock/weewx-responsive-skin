import datetime
import pytz
import time
import dateutil.parser
import syslog
import os.path
import xml.etree.cElementTree as ET

from urllib import urlopen

import weewx.units
from weewx.cheetahgenerator import SearchList

class ausutils(SearchList):
    """Class that implements the '$aus' tag."""

    def __init__(self, generator):
        SearchList.__init__(self, generator)
        self.aus = { "feelslike" : self.feelslikeFunc }
        #put these in the skin_dict so we can change them easily!
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
      
    def get_extension_list(self, timespan, db_lookup):
        return [self]
    
    def feelslikeFunc(self, T_C=None, TS=None):
        if T_C is None or TS is None:
            return None
        try:
            DT = datetime.datetime.fromtimestamp(TS)
            if DT.month >= 10 or DT.month <= 3:
                # October to March
                if DT.hour >= 9 and DT.hour <= 21:
                    #Daytime
                    if T_C >= 37.0:
                        return "Very hot"
                    elif T_C >= 32.0:
                        return "Hot"
                    elif T_C >= 27.0:
                        return "Warm"
                    elif T_C >= 22.0:
                        return "Mild"
                    elif T_C >= 16.0:
                        return "Cool"
                    else:
                        return "Cold"
                else:
                    #Nighttime
                    if T_C >= 22.0:
                        return "Hot"
                    elif T_C >= 18.0:
                        return "Warm"
                    elif T_C >= 15.0:
                        return "Mild"
                    elif T_C >= 10.0:
                        return "Cool"
                    else:
                        return "Cold"             
            else:
                # April to September
                if DT.hour >= 9 or DT.hour <= 21:
                    #Daytime
                    if T_C >= 20.0:
                        return "Warm"
                    elif T_C >= 26.0:
                        return "Mild"
                    elif T_C >= 13.0:
                        return "Cool"
                    elif T_C >= 10.0:
                        return "Cold"
                    else:
                        return "Very cold"
                else:
                    #Nighttime
                    if T_C >= 10.0:
                        return "Mild"
                    elif T_C >= 5.0:
                        return "Cool"
                    elif T_C >= 1.0:
                        return "Cold"
                    else:
                        return "Very cold"
        except:
            return None
                
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

            nextIssue = self.root.find('amoc/next-routine-issue-time-local')
            if nextIssue is not None:
                check_datetime = dateutil.parser.parse(nextIssue.text) + datetime.timedelta(seconds=searcher.staleness_time)
                now_datetime = datetime.datetime.now(pytz.timezone('Australia/Sydney'))
                
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
