import pandas as pd
import csv

BASE = 0x140000000

def merge_skyrim():
    # read address id SSE offsets
    df1 = pd.read_table("offsets-1-5-97-0.csv", sep=",")
    # read address id AE offsets
    df2 = pd.read_table("offsets-1-6-318-0.csv", sep=",")
    # read meh's attempted match table. https://www.nexusmods.com/skyrimspecialedition/mods/32444?tab=files
    df3 = pd.read_table("se-ae-attempted-match.csv", sep=",")
    # read comments from https://github.com/meh321/AddressLibraryDatabase
    df4 = pd.read_table(
        "AddressLibraryDatabase/skyrimae.rename", sep=" ", names=["aeid", "comments"]
    )
    # read Ultra's comment dump for 1.5.97
    df5 = pd.read_table("1.5.97_comments.csv", sep=",")
    output1 = pd.merge(df1, df3, on="sse_addr", how="left")
    output1 = pd.merge(output1, df2, on="ae_addr", how="left")
    output1 = pd.merge(output1, df5, on="sse_addr", how="left")
    output1 = merge_with_override(output1, df4, merge_index="aeid")
    # output map
    output1.to_csv("se_ae_offsets.csv", index=False)

def merge_fo4():
    # read address id fo4 offsets
    df1 = pd.read_table("version-1-10-163-0.csv", sep=",")
    # read ghidra version tracking csv
    df2 = pd.read_table('fo4.csv', sep=',', quoting=csv.QUOTE_ALL)
    df1['fo4_addr'] = df1['fo4_addr'].apply(lambda x: int(x, 16) + BASE)
    df2 = df2[df2["Source Namespace"] == "Global"]
    df2["Source Address"] = df2["Source Address"].apply(lambda x: int(x, 16))
    output1 = pd.merge(df1, df2, left_on="fo4_addr", right_on="Source Address", how="left")
    output1 = output1[output1.Votes > 0]
    output1.to_csv("fo4_fovr_offsets.csv", index=False)
    database = {}
    for index, row in output1.iterrows():
        id = row['id']
        fo4_addr = hex(row['fo4_addr'])
        vr_addr = hex(int(row['Dest Address'], 16))
        status:int = 4 if row['Algorithm'].startswith("Exact Function") else 2
        name = row['Source Label']
        if database.get(id,{}).get('status', 0) < status:
            database[id] = {'fo4': fo4_addr,'vr': vr_addr ,'status': status,'name':name}
    from collections import OrderedDict
    ordered_fieldnames = OrderedDict([('id',None),('fo4',None),('vr',None),('status',None),('name',None)])
    with open('fo4_database.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames = ordered_fieldnames)
        writer.writeheader()
        for key, value in database.items():
            value['id'] = key
            writer.writerow(value)


def merge_with_override(
    base: pd.DataFrame, new: pd.DataFrame, merge_index: str
) -> pd.DataFrame:
    """Merge new dataframe into base dataframe based on merge_index column and overwrite values if base is null.

    Args:
        base (pd.DataFrame): Base dataframe to merge into.
        new (pd.DataFrame): New dataframe
        merge_index (str): Column for merge index. It must exist in both

    Returns:
        pd.DataFrame: Base dataframe with new dataframe merged in where any conflicts resolved in favor of new
    """
    base = pd.merge(base, new, on=merge_index, how="left")
    for col in base.columns:  # find any conflicts
        if col.endswith("_x") and (col[:-2] + "_y") in base.columns:
            override = col[:-2] + "_y"
            base[col] = base[override].combine_first(base[col])
            del base[override]
            base.rename(columns={col: col[:-2]}, inplace=True)
    return base

merge_fo4()
