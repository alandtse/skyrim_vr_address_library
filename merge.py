import pandas as pd

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


output1 = merge_with_override(output1, df4, merge_index="aeid")
# output map
output1.to_csv("se_ae_offsets.csv", index=False)
