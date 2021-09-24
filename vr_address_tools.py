#!/usr/bin/env python3
import argparse
import csv
import fileinput
import os
import re
import CppHeaderParser
from typing import List
import locale

locale.setlocale(locale.LC_ALL, "")  # Use '' for auto, or force e.g. to 'en_US.UTF-8'

HEADER_TYPES = (".h", ".hpp", ".hxx")
SOURCE_TYPES = (".c", ".cpp", ".cxx")
ALL_TYPES = HEADER_TYPES + SOURCE_TYPES
PATTERN = r"rel::id\([^)]+\)"
PATTERN_GROUPS = (
    r"rel::id.*(?:\(|{)\s*(?:([0-9]+)[^)}]*(0x[0-9a-f]*)|([0-9]*))\s*(?:\)|})"
)
RELID_PATTERN = r"(\w+){ REL::ID\(([0-9]+)\),*\s*([a-fx0-9])*\s+};"
OFFSET_PATTERN = r"(\w+){ REL::Offset\(([a-fx0-9]+)\)\s+};"
OFFSET_RELID_PATTERN = r"(?:static|inline) constexpr REL::ID\s+(\w+)\s*\(\s*[^(]+\s*\(\s*([0-9]+)\s*\)\s*\)\s*;"
OFFSET_OFFSET_PATTERN = (
    r"(?:inline|constexpr) REL::Offset\s+(\w+)\s*\(\s*([a-fx0-9]+)\s*\)\s*;"
)
REPLACEMENT = """
#ifndef SKYRIMVR
	{}  // SSE {}
#else
	{}  // TODO: VERIFY {}
#endif
"""
id_sse = {}
id_vr = {}
sse_vr = {}
id_vr_status = {}
debug = False
args = {}
SKYRIM_BASE = "0x140000000"
CONFIDENCE = {
    "UNKNOWN": 0,  # ID is unknown
    "SUGGESTED": 1,  # At least one automated database matched
    "MANUAL": 2,  # One person has confirmed a match
    "VERIFIED": 3,  # Manual + Suggested
}


def add_hex_strings(input1: str, input2: str = "0") -> str:
    """Return sum of two hex strings.

    Args:
        input1 (str): Hex formatted string.
        input2 (str, optional): Hex formatted string. Defaults to "0".

    Returns:
        str: Hex string sum.
    """
    if input1 is None:
        return ""
    return hex(int(input1, 16) + int(input2, 16))


def load_database(
    addresslib="addrlib.csv",
    offsets="offsets-1.5.97.0.csv",
    ida_compare="sse_vr.csv",
    ida_override=True,
) -> int:
    """Load databases.

    Args:
        addresslib (str, optional): Name of csv with VR Address, SSE Address, ID (e.g., 0x1400010d0,0x1400010d0,2). Defaults to "addrlib.csv".
        offsets (str, optional): Name of csv with ID, SSE Address (e.g., 2,10d0). SSE Address is an offset that needs to be added to a base and is dumped from Address Library. Defaults to "offsets-1.5.97.0.csv".
        ida_compare (str, optional): Name of IDADiffCalculator csv with SSE Address, VR Address (e.g., 0x141992C10,0x141A33D38). Defaults to "sse_vr.csv".
        ida_override (bool, optional): Whether IDADiffCalculator will override offsets.
    Returns:
        int: Number of successfully loaded csv files. 0 means none were loaded.
    """
    loaded = 0
    global id_sse
    global id_vr
    global id_vr_status
    global debug
    path = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    try:
        with open(os.path.join(path, "database.csv"), mode="r") as infile:
            reader = csv.DictReader(infile, restval="")
            for row in reader:
                id = int(row["id"])
                sse = add_hex_strings(row["sse"])
                vr = add_hex_strings(row["vr"])
                id_sse[id] = sse
                id_vr[id] = vr
                id_vr_status[id] = {"status": row["status"]}
                loaded += 1
    except FileNotFoundError:
        print(f"database.csv not found")

    try:
        with open(os.path.join(path, addresslib), mode="r") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                id = int(row["id"])
                sse = add_hex_strings(row["sse"])
                vr = add_hex_strings(row["vr"])
                id_sse[id] = sse
                id_vr[id] = vr
                loaded += 1
    except FileNotFoundError:
        print(f"{addresslib} not found")

    try:
        with open(os.path.join(path, offsets), mode="r") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                id = int(row["id"])
                sse = add_hex_strings(f"0x{row['sse']}", SKYRIM_BASE)
                if id_sse.get(id) and id_sse.get(id) != sse:
                    print(
                        f"Database Load Warning: {id} mismatch {sse}	{id_sse.get(id)}"
                    )
                elif id_sse.get(id) is None:
                    id_sse[id] = sse
                loaded += 1
    except FileNotFoundError:
        print(f"{offsets} not found")
    try:
        with open(os.path.join(path, ida_compare), mode="r") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                sse = add_hex_strings(row["sse"])
                vr = add_hex_strings(row["vr"])
                sse_vr[sse] = vr
                loaded += 1
    except FileNotFoundError:
        print(f"{ida_compare} not found")
    if debug:
        print("Combining databases")
    conflicts = 0
    ids = 0
    for id, sse_addr in id_sse.items():
        ids += 1
        ida_addr = add_hex_strings(sse_vr.get(sse_addr))
        if id_vr.get(id) and ida_addr and id_vr.get(id) != ida_addr:
            if ida_override:
                if debug:
                    print(
                        f"Conflict Warning: ID {id} VR {id_vr.get(id)} with IDA {ida_addr}, using IDA"
                    )
                id_vr[id] = ida_addr
            else:
                if debug:
                    print(
                        f"Conflict Warning: ID {id} VR {id_vr.get(id)} with IDA {ida_addr}, ignoring IDA"
                    )
            conflicts += 1
            continue
        elif id not in id_vr and ida_addr:
            id_vr[id] = ida_addr
    if debug:
        print(f"total ids {ids} conflicts {conflicts} percentage {conflicts/ids}")
    return loaded


def scan_code(
    a_directory: str,
    a_exclude: List[str],
) -> dict:
    """Scan code for uses of rel::id and also populate any known id_vr maps from offsets.

    Args:
        a_directory (str): Root directory to walk.
        a_exclude (List[str]): List of file names to ignore.

    Returns:
        results (Dict[str]): Dict of defined_rel_ids, defined_vr_offsets, results
    """
    global debug
    results = []
    defined_rel_ids = {}
    defined_vr_offsets = {}
    count = 0
    for dirpath, dirnames, filenames in os.walk(a_directory):
        rem = []
        for dirname in dirnames:
            if dirname in a_exclude:
                rem.append(dirname)
        for todo in rem:
            dirnames.remove(todo)

        for filename in filenames:
            if filename not in a_exclude and filename.endswith(ALL_TYPES):
                count += 1
                if not filename.lower().startswith("offset"):
                    with open(f"{dirpath}/{filename}") as f:
                        try:
                            for i, line in enumerate(f):
                                matches = re.findall(
                                    PATTERN_GROUPS,
                                    line,
                                    flags=re.IGNORECASE | re.MULTILINE,
                                )
                                if matches:
                                    results.append(
                                        {
                                            "i": i,
                                            "directory": dirpath[len(a_directory) :],
                                            "filename": filename,
                                            "matches": matches,
                                        }
                                    )
                        except UnicodeDecodeError as ex:
                            print(f"Unable to read {dirpath}/{filename}: ", ex)
                else:
                    # looking at offsets
                    if debug:
                        print("parsing offsets file: ", f"{dirpath}/{filename}")
                    header = CppHeaderParser.CppHeader(f"{dirpath}/{filename}")
                    for func in header.functions:
                        if func.get("returns") == "constexpr REL::ID":
                            name = func.get("name")
                            namespace = func.get("namespace")
                            search = re.search(
                                OFFSET_RELID_PATTERN, func.get("debug"), re.I
                            )
                            if search and search.groups():
                                id = search.groups()[1]
                                if debug:
                                    print("Found rel::id", name, id)
                                defined_rel_ids[f"{namespace}{name}"] = {
                                    "id": id,
                                    "func": func,
                                }
                        elif func.get("returns") == "constexpr REL::Offset":
                            name = func.get("name")
                            namespace = func.get("namespace")
                            search = re.search(
                                OFFSET_OFFSET_PATTERN, func.get("debug"), re.I
                            )
                            if search and search.groups():
                                id = search.groups()[1]
                                if debug:
                                    print("Found rel::offset", name, id)
                                defined_vr_offsets[f"{namespace}{name}"] = {
                                    "id": id,
                                    "func": func,
                                }
    print(
        f"Finished scanning {count:n} files. rel_ids: {len(defined_rel_ids)} offsets: {len(defined_vr_offsets)} results: {len(results)}"
    )
    return {
        "defined_rel_ids": defined_rel_ids,
        "defined_vr_offsets": defined_vr_offsets,
        "results": results,
    }


def analyze_code_offsets(defined_rel_ids: dict, defined_vr_offsets: dict):
    """Analyze rel::id and rel::offsets defined in code to mark id_vr items as verified.

    Args:
        defined_rel_ids (dict): rel::ids defined in code. The key is a cpp name designation and the value is the ID.
        defined_vr_offsets (dict): rel::offsets defined in code. The key is a name designation and we assume the same namespace defined as an offset is a VR offset.
    """
    global id_vr_status
    global debug
    if defined_rel_ids and defined_vr_offsets:
        if debug:
            print(
                f"Identifying known offsets from code: {len(defined_rel_ids)} offsets: {len(defined_vr_offsets)}"
            )
        verified = 0
        unverified = 0
        mismatch = 0
        missing = 0
        ida_suggested = 0
        for k, v in defined_vr_offsets.items():
            # Iterate over all discovered vr offsets.
            try:
                if defined_rel_ids.get(k):
                    id = int(defined_rel_ids[k].get("id"))
                    defined_rel_ids[k]["sse"] = sse_addr = add_hex_strings(id_sse[id])
                    bakou_vr_addr = add_hex_strings(id_vr[id])
                    code_vr_addr = add_hex_strings(v.get("id"), SKYRIM_BASE)
                    if sse_vr.get(sse_addr) and sse_vr[sse_addr] != bakou_vr_addr:
                        if debug:
                            print(
                                f"WARNING:{k} IDA {sse_vr[sse_addr]} and bakou {bakou_vr_addr} conversions do not match",
                            )
                    if code_vr_addr == bakou_vr_addr:
                        defined_rel_ids[k]["status"] = CONFIDENCE["VERIFIED"]
                        if debug:
                            print(f"MATCHED: {k} ID: {id} matches database")
                        id_vr_status[id] = defined_rel_ids[k]
                        verified += 1
                    else:
                        if debug:
                            print(
                                f"Potential mismatch with databases: {id} {k} defined: {code_vr_addr} Databases: {bakou_vr_addr} id_sse {sse_addr} sse_vr {sse_vr.get('sse_addr')}",
                            )
                        defined_rel_ids[k]["status"] = CONFIDENCE["MANUAL"]
                        id_vr_status[id] = defined_rel_ids[k]
                        mismatch += 1
            except KeyError:
                id = int(defined_rel_ids[k].get("id"))
                if debug:
                    print(
                        f"Unable to verify: {k} ID: {id} not in databases. id_sse: {id_sse[id]} sse_vr: {sse_vr.get(add_hex_strings(id_sse[id]))}"
                    )
                unverified += 1
        # use databases to suggest addresses for rel::id items
        for k, v in defined_rel_ids.items():
            id = int(v.get("id"))
            if id in id_sse:
                sse_addr = add_hex_strings(id_sse[id])
                v["sse"] = sse_addr
                if (
                    sse_addr in sse_vr
                    and v.get("status", CONFIDENCE["UNKNOWN"]) < CONFIDENCE["MANUAL"]
                ):
                    if debug:
                        print(
                            f"Found suggested address: {sse_vr[sse_addr]} for {k} with IDA. SSE: {sse_addr} "
                        )
                    if v.get("status", CONFIDENCE["UNKNOWN"]) < CONFIDENCE["SUGGESTED"]:
                        v["status"] = CONFIDENCE["SUGGESTED"]
                    elif v.get("status") is None:
                        v["status"] = CONFIDENCE["UNKNOWN"]
                    id_vr_status[id] = v
                    ida_suggested += 1
            if v.get("status", CONFIDENCE["UNKNOWN"]) < CONFIDENCE["MANUAL"]:
                if debug:
                    print(f"Missing VR offset {v.get('id')} for {k} ")
                v["status"] = v.get("status", CONFIDENCE["UNKNOWN"])
                id_vr_status[id] = v
                missing += 1
        print(
            f"Database matched: {verified} ida_suggested: {ida_suggested} unverified: {unverified} mismatch: {mismatch} missing: {missing}"
        )


def match_results(
    results: List[dict], min_confidence=CONFIDENCE["SUGGESTED"]
) -> List[dict]:
    """Match result ids to known vr addresses that meet min_confidence.

    Args:
        results (List[dict]): A list of results from scan_code
        mind_confidence (int, optional): Minimum confidence level to match. Defaults to SUGGESTED == 1

    Returns:
        List[dict]: [description]
    """
    global id_vr_status
    new_results = []
    for result in results:
        i = result["i"]
        directory = result["directory"]
        filename = result["filename"]
        matches = result["matches"]
        offset = 0
        conversion = ""
        vr_addr = ""
        warning = ""
        for match in matches:
            if match[0]:
                id = int(match[0])
                try:
                    offset = match[1]
                except ValueError:
                    offset = 0
            else:
                id = int(match[2])
                offset = 0
            if (
                id_vr.get(id)
                and int(id_vr_status.get(id, {}).get("status", 0)) >= min_confidence
            ):
                vr_addr = id_vr[id]
                conversion = f"REL::Offset(0x{vr_addr[4:]})"
                if offset:
                    warning = f"WARNING: Offset detected; offset may need to be manually updated for VR"
            if not vr_addr:
                warning += f"WARNING: VR Address undefined."
            try:
                sse_addr = id_sse[id]
            except KeyError:
                conversion = "UNKNOWN"
                sse_addr = ""
            if offset and not conversion:
                conversion = f"UNKNOWN SSE_{sse_addr}{f'+{offset}={add_hex_strings(sse_addr, offset)}' if offset else ''}"
            new_results.append(
                f"{directory}/{filename}:{i+1}\tID: {id}\tSSE: {sse_addr}\t{conversion}\t{vr_addr}\t{warning}"
            )
    return new_results


def in_file_replace(results: List[str]) -> bool:
    """Replace instances of REL::ID with an #ifndef SKYRIMVR.

    Args:
        results (List[str]): [description]

    Returns:
        bool: Whether successful
    """
    for line in results:
        parts = line.split("\t")
        print(parts)
        filename, line_number = parts[0].split(":")
        text_to_replace = parts[1]
        sse_addr = parts[2]
        vr_addr = parts[4]
        if parts[3].startswith("UNKNOWN"):
            replacement = f"REL::Offset({parts[3]})"
        else:
            replacement = parts[3]
        with fileinput.FileInput(filename, inplace=True) as file:
            print(f"Performing replace for {parts[0]}")
            found_ifndef = False
            for i, line in enumerate(file):
                if "#ifndef SKYRIMVR".lower() in line.lower():
                    found_ifndef = True
                    print(line, end="")
                elif found_ifndef and text_to_replace in line:
                    found_ifndef = False
                    print(line, end="")
                else:
                    print(
                        line.replace(
                            text_to_replace,
                            REPLACEMENT.format(
                                text_to_replace,
                                sse_addr,
                                replacement,
                                vr_addr,
                            ),
                        ),
                        end="",
                    )
    return True


def write_csv(
    file_prefix: str = "version",
    version: str = "1-4-15-0",
    min_confidence=CONFIDENCE["MANUAL"],
    generate_database=False,
    release_version="0.0.0",
) -> bool:
    """Generate csv file.

    Args:
        file_prefix (str, optional): Filename prefix to output. Defaults to "version".
        version (str, optional): Version suffix. Defaults to "1-4-15-0".
        min_confidence (int, optional): Minimum confidence to output. Defaults to CONFIDENCE["MANUAL"] == 2.
        generate_database (bool, optional): Whether to generate a database file (used for GitHub editing) instead of an importable address.csv. Defaults to False.
        release_version (str, optional): CSV version. Defaults to "0.0.0".
    Returns:
        bool: Whether successful.
    """
    global id_vr_status
    outputfile = (
        f"{file_prefix}-{version}.csv" if not generate_database else f"database.csv"
    )
    output = {}
    if min_confidence is not None and isinstance(min_confidence, int):
        output = dict(
            filter(
                lambda elem: (
                    id_vr_status.get(elem[0])
                    and id_vr_status.get(elem[0]).get("status", 0)
                    and int(id_vr_status.get(elem[0]).get("status", 0))
                    >= min_confidence
                )
                or (min_confidence == 0 and elem[0] not in id_vr_status),
                id_vr.items(),
            )
        )
        print(
            f"Filtered {len(id_vr)} to {len(output)} using min_confidence {min_confidence}"
        )
    else:
        output = id_vr
    try:
        with open(outputfile, "w", newline="") as f:
            writer = csv.writer(f)
            rows = len(output)
            if not generate_database:
                writer.writerow(("id", "offset"))
                writer.writerow((rows, release_version))
                for id, address in sorted(output.items()):
                    writer.writerow((id, address[4:]))
            else:
                writer.writerow(("id", "sse", "vr", "status", "name"))
                for id, address in sorted(output.items()):
                    sse_addr = ""
                    status = ""
                    name = ""
                    if id_vr_status.get(id):
                        entry = id_vr_status.get(id)
                        sse_addr = entry.get("sse", "")
                        status = entry["status"]
                        if entry.get("func"):
                            name = (
                                f'{entry["func"]["namespace"]}{entry["func"]["name"]}'
                            )
                    writer.writerow((id, sse_addr, address, status, name))
            print(
                f"Wrote {rows} rows into {outputfile} with release version {release_version}"
            )
            return True
    except OSError as ex:
        print(f"Error writing to {outputfile}: {ex}")
        return False


def main():
    global debug
    global args
    parser = argparse.ArgumentParser(
        description="Find uses of REL::ID in cpp files. By default, performs a lint to display a list of files besides Offsets*.h which are using REL::ID and should be converted for VR. Unknown addresses will be prefaced SSE_."
    )

    def dir_path(path):
        if os.path.isdir(path):
            return path
        else:
            raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")

    parser.add_argument("path", help="Path to the input directory.", type=dir_path)

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Print debug messages.",
    )
    subparsers = parser.add_subparsers(dest="subparser")

    parser_analyze = subparsers.add_parser(
        "analyze",
        help="Analyze code to determine manually identified ids and vr offsets. Will also check against bin-diffed address databases.",
    )
    parser_analyze.add_argument(
        "--min",
        nargs="?",
        const="minimum",
        action="store",
        help="Sets the minimum confidence for the csv. Defaults to 2.",
    )

    parser_replace = subparsers.add_parser(
        "replace",
        help="Replace files automatically inline with bin-diffed discovered addresses within an #ifndef SKYRIMVR. Unknown addresses will be prefaced SSE_ and need to be manually fixed. This should be used for quick address testing only because it is preferred to make fixes in a new VR csv.",
    )
    parser_generate = subparsers.add_parser(
        "generate",
        help="Generate a version-1.4-15.0.csv with offsets.",
    )
    parser_generate.add_argument(
        "--prefix",
        nargs="?",
        const="version",
        action="store",
        help="Sets the prefix for the csv. Defaults to version.",
    )
    parser_generate.add_argument(
        "--min",
        nargs="?",
        const="minimum",
        action="store",
        help="Sets the minimum confidence for the csv. Defaults to 2.",
    )
    parser_generate.add_argument(
        "-d",
        "--database",
        action="store_true",
        help="Generate database.csv.",
    )
    parser_generate.add_argument(
        "-rv",
        "--release_version",
        nargs="?",
        const="release_version",
        action="store",
        help="Sets the release version. Defaults to 0.0.0.",
    )

    args = vars(parser.parse_args())
    debug = args.get("debug")
    if debug:
        print(args)
    exclude = ["build", "extern"]
    scan_results = {}
    # Load files from location of python script
    if (
        load_database(
            ida_override=True,
        )
        == 0
    ):
        print("Error, no databases loaded. Exiting.")
        exit(1)
    else:
        if args["path"]:
            root = args["path"]
            os.chdir(root)
        else:
            root = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]
            os.chdir(root)
        scan_results = scan_code(
            root,
            exclude,
        )
    analyze = args.get("subparser") == "analyze"
    replace = args.get("subparser") == "replace"
    generate = (
        args.get("prefix")
        if args.get("subparser") == "generate" and args.get("prefix")
        else args.get("subparser") == "generate"
    )
    defined_rel_ids = scan_results["defined_rel_ids"]
    defined_vr_offsets = scan_results["defined_vr_offsets"]
    minimum = 2
    if args.get("min") is not None:
        minimum = int(args.get("min"))
    analyze_code_offsets(defined_rel_ids, defined_vr_offsets)
    if generate:
        sub_args = {"min_confidence": minimum}
        if args.get("database"):
            sub_args["generate_database"] = True
        if generate and not isinstance(generate, bool):
            sub_args["file_prefix"] = generate
        if args.get("release_version"):
            sub_args["release_version"] = args.get("release_version")
        write_csv(**sub_args)
    elif analyze and scan_results.get("results"):
        results = match_results(scan_results["results"], min_confidence=minimum)
        results.sort()
        if replace:
            in_file_replace(results)
        else:
            print(*results, sep="\n")
            print(f"Found {len(results):n} items")
            exit(len(results))


if __name__ == "__main__":
    main()
