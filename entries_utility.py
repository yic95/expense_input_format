#!/usr/bin/python
import sys


def parse_single_dsl_entry(string: str, multiple_date: bool=False):
    """Parse the string as a single entry with falsy default value.

    The DSL is specified as follows:
        entry   ::= [expense] [segment]* [title]
        expense ::= digits
        segment ::= segment-prefix [segment-content]
        segment-prefix  ::= ':' | '@'  # [colon] for tags; [at] for date
        segment-content ::= [char - ',' - '@' - '/']*
        title   ::= '/' [string]
    The result includes keys "expense", "date", "tags" and "title" with
    falsy default value. The "date" element can only be specified once
    unless `multiple_date` is true. 
    """
    info = {'expense': "",
            'title': "",
            'date': [] if multiple_date else "",
            'tags': []}
    def store_segment(seg_type, seg, buf):
        if seg_type == 'tags':
            buf['tags'].append("".join(seg))
        elif seg_type == 'date' and multiple_date:
            buf['date'].append("".join(seg))
        else:
            buf[seg_type] = "".join(seg)
    segment = []
    segment_type = "expense"

    for i in string:
        if i in {'\0', '\n', '\r', '\t'}:
            continue
        if i == '/' and segment_type != 'title':
            store_segment(segment_type, segment, info)
            segment.clear()
            segment_type = 'title'
        elif i == '@' and segment_type != 'title':
            store_segment(segment_type, segment, info)
            segment.clear()
            segment_type = 'date'
        elif i == ':' and segment_type != 'title':
            store_segment(segment_type, segment, info)
            segment.clear()
            segment_type = 'tags'
        else:
            segment.append(i)
    store_segment(segment_type, segment, info)
    return info


def parse_arguemnt_entries(arguments: [str]) -> [dict]:
    """Parse a string as single or multiple entries.

    If the substring after the first space is of segment type 'title',
    the entire string is parsed as a single entry, with the substring
    being part of the title. Otherwise, the entire string is parsed as
    multiple entries, seperated by spaces.
    """
    result = []
    if not arguments:
        return result
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


def parse_tsv_entries(entries: [str], skip_header: bool = False) -> [dict]:
    columns = ('date', 'seq', 'expense', 'title', 'tags')
    start = 1 if skip_header else 0
    result = []
    for row in entries[start::] :
        ent_dict = {'date': '',
                    'seq': '',
                    'expense': '',
                    'title': '',
                    'tags': []}
        for name, cell in zip(columns, row.split('\t')):
            if cell == '::::':
                continue
            if name == 'tags':
                if len(cell) > 3:
                    ent_dict[name] = cell[2:-2:].split('::')
            else:
                ent_dict[name] = cell
        result.append(ent_dict)

    return result


def format_entry(entries: [dict]) -> [str]:
    """Format entries into list of TSV rows.

    The columns are: 'date', 'seq', 'expense', 'title', 'tags'. The
    tags are seperated and surrounded by double colon (::).
    The result does not include column title.
    """
    result = []
    for ent in entries:
        fmt_ent = []
        if 'date' in ent and ent['date']:
            fmt_ent.append(ent['date'])
        else:
            fmt_ent.append('::::')
        fmt_ent.append('\t')

        if 'seq' in ent and ent['seq']:
            fmt_ent.append(ent['seq'])
        fmt_ent.append('\t')

        if 'expense' in ent and ent['expense']:
            fmt_ent.append(ent['expense'])
        fmt_ent.append('\t')

        if 'title' in ent and ent['title']:
            fmt_ent.append(ent['title'])
        else:
            fmt_ent.append('::::')
        fmt_ent.append('\t')

        if 'tags' in ent:
            # empty tag field will be formatted as "::::"
            fmt_ent.append('::')
            if ent['tags']:
                for t in ent['tags'][0:-1:]:
                    fmt_ent.append(t)
                    fmt_ent.append('::')
                fmt_ent.append(ent['tags'][-1])
            fmt_ent.append('::')

        result.append("".join(fmt_ent))

    return result


def fix_tag_hierarchy(entries: [dict], hier: dict[str, str]) -> [dict]:
    """Remove repeated tags and add the parent tag of each tag.

    The keys of hier is a child tag of their value. No order is preserved.
    """
    for ent in entries:
        result = set()
        for t in ent['tags']:
            tag = t
            result.add(tag)
            while tag in hier and hier[tag] not in result:
                result.add(hier[tag])
                tag = hier[tag]
        ent['tags'] = list(result)

    return entries


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
    would be preserved, and are guaranteed to be unique among the list.
    """
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


def is_hierarchy_valid(hier: dict[str, str]) -> bool:
    """Return True if there are no cycles or loops"""
    valid_nodes = set()
    for node_checking in hier:
        if node_checking in valid_nodes:
            continue
        history_node = set(node_checking)
        k = node_checking
        while k in hier:
            k = hier[k]
            if k in history_node:
                return False
            history_node.add(k)
        valid_nodes |= history_node
    return True


def parse_query_string(query: str) -> dict:
    entry = parse_single_dsl_entry(query, multiple_date=True)
    for k in ('date', 'tags'):
        entry[k] = [s.split(',') for s in entry[k]]
    if 'expense' in entry:
        entry['expense'] = entry['expense'].split(',')
    return entry


if __name__ == '__main__':
    idol_ent = parse_query_string(sys.argv[1])
    print(idol_ent)
