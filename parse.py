#!/usr/bin/python
import sys


def parse_single_dsl_entry(string: str):
    """Parse the string as a single entry.

    The string is seperated into typed segments by [comma], [at],
    [slash]. The segment type is determined by the seperator in front
    of the segment: Commas for 'tags', ats for 'date', slash for
    'title'. Only segments of type 'tags' can be specified multiple
    times. If other segment types are repeated, only the first will be
    used. The first segment is of type 'expense', and all characters
    after the first slash in the string will be parsed as part of title.
    """
    # TODO Add dot-escaped literal character
    info = {'expense': "",
            'title': "",
            'date': "",
            'tags': []}
    def store_segment(seg_type, seg, buf):
        if seg_type == 'tags':
            buf['tags'].append(''.join(seg))
        elif seg_type == 'date' and buf['date'] == "":
            buf['date'] = ''.join(seg)
        elif seg_type == 'expense' and buf['expense'] == "":
            buf['expense'] = ''.join(seg)
        elif seg_type == 'title' and buf['title'] == "":
            buf['title'] = ''.join(seg)
    segment = []
    segment_type = "expense"

    for i in string:
        if i == '/' and segment_type != 'title':
            store_segment(segment_type, segment, info)
            segment.clear()
            segment_type = 'title'
        elif i == '@' and segment_type != 'title':
            store_segment(segment_type, segment, info)
            segment.clear()
            segment_type = 'date'
        elif i == ',' and segment_type != 'title':
            store_segment(segment_type, segment, info)
            segment.clear()
            segment_type = 'tags'
        else:
            segment.append(i)
    store_segment(segment_type, segment, info)
    info['tags'].sort()
    return info


def parse_arguemnt_entries(arguments: [str], default_info: dict = False) -> [dict]:
    """Parse a string as single or multiple entries.

    If the substring after the first space is of segment type 'title',
    the entire string is parsed as a single entry, with the substring
    being part of the title. Otherwise, the entire string is parsed as
    multiple entries, seperated by spaces.
    """
    if not default_info:
        default_info = {}
    default_keys = default_info.keys()
    result = []
    if len(arguments) < 2 \
        or (not set(arguments[1]).intersection(set('/,@'))
            and not arguments[1].isnumeric()):
        result.append(
                parse_single_dsl_entry(" "
                                       .join(arguments)
                                       .replace(' ', '/')))
    else:
        for e in arguments:
            result.append(parse_single_dsl_entry(e))
    return result


def format_entry(entry_info: dict) -> str:
    """Format entry information into TSV.

    The columns are: 'date', 'seq', 'expense', 'tags and title'. The
    tags are prepended in front of title, seperated and surrounded by
    double colon (::). The result does not include column title.
    """
    result = []
    if 'date' in entry_info and entry_info['date']:
        result.append(entry_info['date'])
    result.append('\t')

    if 'seq' in entry_info and entry_info['seq']:
        result.append(entry_info['seq'])
    result.append('\t')

    if 'expense' in entry_info and entry_info['expense']:
        result.append(entry_info['expense'])
    result.append('\t')
    
    if 'tags' in entry_info and entry_info['tags']:
        result.append('::')
        for t in entry_info['tags']:
            result.append(t)
            result.append('::')

    if 'title' in entry_info and entry_info['title']:
        result.append(entry_info['title'])
    result.append('\n')

    return ''.join(result)


def fix_tag_hierarchy(entries: [dict], hier) -> [dict]:
    pass


def add_default_info(entries: [dict], info: dict):
    """Add default informations specified in info.

    For key 'tags' specifically, the entries is extended with 'tags' in
    info, and are not guranteed to be unique.
    """
    for dk, dv in info.items():
        if dk == 'tags':
            for ent in entries:
                if 'tags' in ent:
                    ent['tags'].extend(dv)
                else:
                    ent['tags'] = dv.clone()
        else:
            for ent in entries:
                if dk not in ent or not ent[dk]:
                    ent[dk] = dv

def add_sequence_number(entries: [dict],
                        start: int = 1,
                        overwrite: bool = False):
    """Add sequence number to entries, starting at `start`, step by 1.

    If `overwrite` is False, the original sequence numbers of entries 
    would be preserved, and are guaranteed to be unique among the list."""
    existing_seq = []
    if not overwrite:
        for ent in entries:
            if 'seq' in ent and int(ent['seq']) >= start:
                existing_seq.append(int(ent['seq']))

    seq_num = start
    for ent in entries:
        while seq_num in existing_seq:
            seq_num += 1
        if 'seq' not in ent or not ent['seq'] or overwrite:
            ent['seq'] = str(seq_num)
            seq_num += 1


if __name__ == '__main__':
    tinfos = parse_arguemnt_entries(sys.argv[1::])
    add_default_info(tinfos, {'title': '--untitled--'})
    add_sequence_number(tinfos)
    
    #print(tinfos)
