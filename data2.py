import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = "pittsburgh_pennsylvania.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
states_re = re.compile('^[a-z]{2}$')
states_fullname_re = re.compile('[A-Z][a-z]+')
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

States = { "Pennsylvania": "PA", "Ohio": "OH", "West Virginia": "WV", "pa": "PA", "oh": "OH", "wv":"WV"}
mapping = { "Ave": "Avenue", "Dr": "Drive"}

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements
    
    if element.tag == "node":
    	
            	            	    	    
        for l in NODE_FIELDS:
            node_attribs[l] = element.attrib[l]
        

        for m in element.iter('tag'):
            a={}
            b={}

            if PROBLEMCHARS .search(m.attrib['k']):
                pass

            elif LOWER_COLON.search(m.attrib['k']):
                b['id']= element.attrib['id']
                colsplit = (m.attrib['k']).split(':')
                j = colsplit[0]
                b['type'] = j
                b['value'] = m.attrib['v']
                b['key'] = (m.attrib['k'])[(m.attrib['k']).find(":")+1:]
                tags.append(b)
                if m.attrib['k'] == "addr:state":
                    b['value'] = update_name(m.attrib['v'], States)
#                     tags.append(b)
                elif m.attrib['k']=='addr:street':
					b['value'] = update_street(m.attrib['v'], mapping)
# 					tags.append(b)
            else:
                a['id']= element.attrib['id']
                a['key'] = m.attrib['k']
                a['value'] = m.attrib['v']
                a['type'] = 'regular'
                tags.append(a)
                if m.attrib['k'] == "addr:state":
                    a['value'] = update_name(m.attrib['v'], States) 
#                     tags.append(a)
                elif m.attrib['k']=='addr:street':
					a['value'] = update_street(m.attrib['v'], mapping) 
# 					tags.append(a)
        
    if element.tag == "way":
            	    
        for n in WAY_FIELDS:
            way_attribs[n] = element.attrib[n]
            
        for o in element.iter('tag'):
            c={}
            d={}

            if PROBLEMCHARS.search(o.attrib['k']):
                pass

            elif LOWER_COLON.search(o.attrib['k']):
                c['id']= element.attrib['id']
                colsplit = (o.attrib['k']).split(':')
                j = colsplit[0]
                c['type'] = j
                c['value'] = o.attrib['v']
                c['key'] = (o.attrib['k'])[(o.attrib['k']).find(":")+1:]
                tags.append(c)
                if o.attrib['k'] == "addr:state":
                	c['value'] = update_name(o.attrib['v'], States)
#                 	tags.append(c)
                elif o.attrib['k']=='addr:street':
					c['value'] = update_street(o.attrib['v'], mapping) 
# 					tags.append(c)
            else:
                d['id']= element.attrib['id']
                d['key'] = o.attrib['k']
                d['value'] = o.attrib['v']
                d['type'] = 'regular'
                tags.append(d)
                if o.attrib['k'] == "addr:state":
                    d['value'] = update_name(o.attrib['v'], States) 
#                     tags.append(d)
                elif o.attrib['k']=='addr:street':
					d['value'] = update_street(o.attrib['v'], mapping)
# 					tags.append(d)
			
        count = 0
        for o in element.iter('nd'):
            e={}           
            e['id']= element.attrib['id']
            e['node_id'] = o.attrib['ref']
            e['position'] = count
            count+=1
            way_nodes.append(e)
        

		
    if element.tag == 'node':
        return {'node': node_attribs, 'node_tags': tags}
        
    elif element.tag == 'way':
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def update_name(st_name, States):
	stfl = states_fullname_re.search(st_name)
	stlc = states_re.search(st_name)
	
	if stfl:
		flstate_type = stfl.group()
		if flstate_type in States.keys():
			st_name = re.sub(flstate_type, States[flstate_type], st_name)
	
	elif stlc:
		lcstate_type = stlc.group()
		if lcstate_type in States.keys():
			st_name = re.sub (lcstate_type, States[lcstate_type], st_name)
	return st_name

def update_street(street_name, mapping):
	u = street_type_re.search(street_name)
	if u:
		street_type = u.group()
		if street_type in mapping.keys():
			street_name = re.sub (street_type, mapping[street_type], street_name)

	return street_name



# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)
