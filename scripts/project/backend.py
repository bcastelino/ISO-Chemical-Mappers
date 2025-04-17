#new backend.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
from fuzzywuzzy import process
import traceback
import numpy as np
from typing import List, Optional

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Excel
file_path = "https://www.dropbox.com/scl/fi/gf21i2qf3ffioy958448x/Data-Model-Tables.xlsx?rlkey=4ovpu5v0l7ri0zp3bi5wx3u0t&st=6xle6bd9&dl=1"

ref_df = pd.read_excel(file_path, sheet_name="Substance_Reference")
source_df = pd.read_excel(file_path, sheet_name="Substance_Sourcing")
weight_df = pd.read_excel(file_path, sheet_name="Weighting_Tag").apply(lambda x: x.astype(str).str.strip())
substance_type_df = pd.read_excel(file_path, sheet_name="Substance_Type").apply(lambda x: x.astype(str).str.strip())

# Clean and standardize IDs
ref_df["Substance_Reference_ID"] = ref_df["Substance_Reference_ID"].astype(str).str.strip().str.replace('.0', '', regex=False)
ref_df["Substance_ID"] = ref_df["Substance_ID"].astype(str).str.strip()
ref_df["Substance_Name"] = ref_df["Substance_Name"].astype(str).fillna("Not Available").str.strip()
ref_df["Substance_Description"] = ref_df["Substance_Description"].astype(str).fillna("Not Available").str.strip()
ref_df["Substance_Weight"] = ref_df.get("Substance_Weight", "Not Available").astype(str).fillna("Not Available").str.strip()
ref_df["(FK) Weighting_Tag_ID"] = ref_df["(FK) Weighting_Tag_ID"].astype(str).str.strip()

source_df["(FK) Substance_ID"] = source_df["(FK) Substance_ID"].astype(str).str.strip().str.replace('.0', '', regex=False)
source_df["Substance_Sourcing_Local_Name"] = source_df["Substance_Sourcing_Local_Name"].astype(str).str.strip()

weight_df["Weighting_Tag_ID"] = weight_df["Weighting_Tag_ID"].astype(str).str.strip()

ref_with_weight_title_df = ref_df.merge(
    weight_df[["Weighting_Tag_ID", "Weighting_Tag_Title"]],
    left_on="(FK) Weighting_Tag_ID",
    right_on="Weighting_Tag_ID",
    how="left"
).fillna("Not Available")

ref_df = ref_with_weight_title_df
combined_df = pd.merge(
    source_df,
    ref_df,
    left_on="(FK) Substance_ID",
    right_on="Substance_Reference_ID",
    how="left"
).fillna("Not Available")

class MatchResult(BaseModel):
    substance_reference_id: str
    substance_id: str
    matched_text: str
    match_type: str
    score: int
    substance_name: str
    description: str
    weight: str
    total_synonyms_matched: Optional[int] = None
    weight_tag_title: Optional[str] = None


@app.get("/match", response_model=List[MatchResult])
def match_substance(query: str = Query(...)):
    query_lower = query.strip().lower()
    results = []
    seen_ref_ids = set()

    def get_synonym_count(sub_ref_id: str) -> int:
        try:
            sub_ref_id = str(sub_ref_id).strip()
            filtered = combined_df[
                combined_df["Substance_Reference_ID"].astype(str).str.strip() == sub_ref_id
            ]
            return int(filtered["Substance_Sourcing_Local_Name"].nunique())
        except Exception:
            return 0

    # --------- Exact CAS match ----------
    for _, row in ref_df[ref_df["Substance_ID"].str.lower() == query_lower].iterrows():
        if row["Substance_Reference_ID"] not in seen_ref_ids:
            results.append(MatchResult(
                substance_reference_id=row["Substance_Reference_ID"],
                substance_id=row["Substance_ID"],
                matched_text=query,
                match_type="exact-CAS",
                score=100,
                substance_name=row["Substance_Name"],
                description=row["Substance_Description"],
                weight=row["Substance_Weight"],
                total_synonyms_matched=get_synonym_count(row["Substance_Reference_ID"]),
                weight_tag_title=row["Weighting_Tag_Title"]
            ))
            seen_ref_ids.add(row["Substance_Reference_ID"])

    # --------- Exact Substance Name match ----------
    for _, row in ref_df[ref_df["Substance_Name"].str.lower() == query_lower].iterrows():
        if row["Substance_Reference_ID"] not in seen_ref_ids:
            results.append(MatchResult(
                substance_reference_id=row["Substance_Reference_ID"],
                substance_id=row["Substance_ID"],
                matched_text=query,
                match_type="exact-substance name",
                score=100,
                substance_name=row["Substance_Name"],
                description=row["Substance_Description"],
                weight=row["Substance_Weight"],
                total_synonyms_matched=get_synonym_count(row["Substance_Reference_ID"]),
                weight_tag_title=row["Weighting_Tag_Title"]
            ))
            seen_ref_ids.add(row["Substance_Reference_ID"])

    # --------- Exact Synonym match ----------
    synonym_matches = combined_df[combined_df["Substance_Sourcing_Local_Name"].str.lower() == query_lower]
    for _, row in synonym_matches.head(3).iterrows():
        if row["Substance_Reference_ID"] != "Not Available" and row["Substance_Reference_ID"] not in seen_ref_ids:
            results.append(MatchResult(
                substance_reference_id=row["Substance_Reference_ID"],
                substance_id=row["Substance_ID"],
                matched_text=row["Substance_Sourcing_Local_Name"],
                match_type="exact-synonym",
                score=100,
                substance_name=row["Substance_Name"],
                description=row["Substance_Description"],
                weight=row["Substance_Weight"],
                total_synonyms_matched=get_synonym_count(row["Substance_Reference_ID"]),
                weight_tag_title=row["Weighting_Tag_Title"]
            ))
            seen_ref_ids.add(row["Substance_Reference_ID"])

    # --------- Fuzzy Matching with score-first, then type-priority ---------
    if not results:
        substance_name_pool = ref_df["Substance_Name"].dropna().unique()
        synonym_pool = combined_df["Substance_Sourcing_Local_Name"].dropna().unique()

        fuzzy_candidates = []

        # Fuzzy match on Substance Name
        fuzzy_name_matches = process.extract(query, substance_name_pool, limit=10)
        for match_text, score in fuzzy_name_matches:
            match_text_lower = match_text.lower()
            matched_rows = ref_df[ref_df["Substance_Name"].str.lower() == match_text_lower]
            for _, r in matched_rows.iterrows():
                fuzzy_candidates.append({
                    "type": "fuzzy-substance name",
                    "score": score,
                    "text": match_text,
                    "sub_ref_id": r["Substance_Reference_ID"],
                    "sub_id": r["Substance_ID"],
                    "name": r["Substance_Name"],
                    "desc": r["Substance_Description"],
                    "weight": r["Substance_Weight"],
                    "tag_title": r["Weighting_Tag_Title"]
                })

        # Fuzzy match on Synonym
        fuzzy_synonym_matches = process.extract(query, synonym_pool, limit=10)
        for match_text, score in fuzzy_synonym_matches:
            match_text_lower = match_text.lower()
            matched_rows = combined_df[combined_df["Substance_Sourcing_Local_Name"].str.lower() == match_text_lower]
            for _, r in matched_rows.iterrows():
                if r["Substance_Reference_ID"] != "Not Available":
                    fuzzy_candidates.append({
                        "type": "fuzzy-synonym",
                        "score": score,
                        "text": match_text,
                        "sub_ref_id": r["Substance_Reference_ID"],
                        "sub_id": r["Substance_ID"],
                        "name": r["Substance_Name"],
                        "desc": r["Substance_Description"],
                        "weight": r["Substance_Weight"],
                        "tag_title": r["Weighting_Tag_Title"]
                    })

        # Sort by score descending, then by type priority
        type_priority = {
            "fuzzy-substance name": 1,
            "fuzzy-synonym": 2
        }

        fuzzy_sorted = sorted(
            fuzzy_candidates,
            key=lambda x: (-x["score"], type_priority.get(x["type"], 99))
        )

        fuzzy_results_added = 0
        for item in fuzzy_sorted:
            if item["sub_ref_id"] in seen_ref_ids:
                continue
            results.append(MatchResult(
                substance_reference_id=item["sub_ref_id"],
                substance_id=item["sub_id"],
                matched_text=item["text"],
                match_type=item["type"],
                score=item["score"],
                substance_name=item["name"],
                description=item["desc"],
                weight=item["weight"],
                total_synonyms_matched=get_synonym_count(item["sub_ref_id"]),
                weight_tag_title=item["tag_title"]
            ))
            seen_ref_ids.add(item["sub_ref_id"])
            fuzzy_results_added += 1
            if fuzzy_results_added >= 3:
                break

    # --------- Final priority-based sorting ----------
    if results:
        return results

    # --------- No Match Fallback ----------
    return [MatchResult(
        substance_reference_id="NOT FOUND",
        substance_id="NOT FOUND",
        matched_text=query,
        match_type="no match",
        score=0,
        substance_name="Not Available",
        description="Not Available",
        weight="Not Available",
        total_synonyms_matched=0,
        weight_tag_title="Not Available"
    )]
#------------------Synonyms------------------------------
@app.get("/synonyms_lookup")
def get_related_synonyms(term: str = Query(...)):
    term = term.strip().lower()

    matched_ref_ids = ref_df[ref_df["Substance_Name"].str.lower() == term]["Substance_Reference_ID"].tolist()
    synonym_matched_ids = combined_df[combined_df["Substance_Sourcing_Local_Name"].str.lower() == term]["Substance_Reference_ID"].tolist()

    all_ids = list(set(matched_ref_ids + synonym_matched_ids))

    if not all_ids:
        return {"found": False, "term": term, "synonyms": []}

    related = combined_df[combined_df["Substance_Reference_ID"].isin(all_ids)]

    grouped = related.groupby("Substance_Reference_ID").agg({
        "Substance_Sourcing_Local_Name": lambda x: sorted(set(x.dropna())),
        "Substance_ID": "first",
        "Substance_Name": "first"
    }).reset_index()

    return grouped.to_dict(orient="records")
@app.get("/synonyms")
def get_synonym_insights():
    
    try:

        # Unique synonym → # of unique substances it maps to
        synonym_counts = (
            source_df.groupby("Substance_Sourcing_Local_Name")["(FK) Substance_ID"]
            .nunique()
            .reset_index(name="Distinct Substance Count")
        )
 
        multi_substance_synonyms = synonym_counts[synonym_counts["Distinct Substance Count"] > 1]
        single_substance_synonyms = synonym_counts[synonym_counts["Distinct Substance Count"] == 1]
 
        top_ambiguous = multi_substance_synonyms.sort_values("Distinct Substance Count", ascending=False).head(10)
 
        # Synonym Distribution by how many substances they map to
        dist_df = synonym_counts["Distinct Substance Count"].value_counts().reset_index()
        dist_df.columns = ["Mapped Substances", "Synonym Count"]
        dist_df = dist_df.sort_values("Mapped Substances")
 
        # Substances with Most Synonyms
        top_substances = (
            source_df.groupby("(FK) Substance_ID")["Substance_Sourcing_Local_Name"]
            .nunique()
            .reset_index(name="Synonym Count")
            .sort_values("Synonym Count", ascending=False)
            .merge(ref_df, left_on="(FK) Substance_ID", right_on="Substance_Reference_ID", how="left")
            [["Substance_ID", "Substance_Name", "Synonym Count"]]
            .head(10)
        )
        # Load the correct sheets
        substance_type_df = pd.read_excel(file_path, sheet_name="Substance_Type").apply(lambda x: x.astype(str).str.strip())  # Correct sheet
        source_type_df = pd.read_excel(file_path, sheet_name="Substance_Sourcing_Type").apply(lambda x: x.astype(str).str.strip())
        weight_df = pd.read_excel(file_path, sheet_name="Substance_Weighting_Tag").apply(lambda x: x.astype(str).str.strip())
        tag_map_df = pd.read_excel(file_path, sheet_name="Weighting_Tag").apply(lambda x: x.astype(str).str.strip())
 
        # Ensure the 'Substance_Type_Title' exists in the Substance_Type sheet
        if "Substance_Type_Title" not in substance_type_df.columns:
            return JSONResponse(content={"error": "'Substance_Type_Title' column is missing from Substance_Type sheet"}, status_code=500)
 
        # Now referencing the correct sheet for Substance_Type_ID and Substance_Type_Title
        substance_type_df["Substance_Type_ID"] = substance_type_df["Substance_Type_ID"].astype(str).str.strip()
 
        # Now proceed with your analysis
        ref_df["_Substance_Type_ID"] = ref_df.get("(FK) Substance_Type_ID", "Not Available").astype(str).str.strip()
 
        # Merge the data based on the correct reference
        ref_with_type = ref_df.merge(
            substance_type_df,
            left_on="_Substance_Type_ID",
            right_on="Substance_Type_ID",
            how="left"
        )
 
        substances_per_type = (
            ref_with_type["Substance_Type_Title"]  # Correct column for title
            .value_counts()
            .reset_index()
            .rename(columns={"index": "Substance Type", "Substance_Type_Title": "Count"})
        )
 
        # Continue with the rest of the analysis...
        top_synonyms = (
            source_df.groupby("(FK) Substance_ID")["Substance_Sourcing_Local_Name"]
            .count()
            .reset_index(name="Synonym Count")
            .sort_values("Synonym Count", ascending=False)
            .head(10)
            .merge(ref_df, left_on="(FK) Substance_ID", right_on="Substance_Reference_ID", how="left")
            [["Substance_ID", "Substance_Name", "Synonym Count"]]
        )
 
        # Substances per Weight Tag
        tag_counts = weight_df["(FK) Weighting_Tag_ID"].value_counts().reset_index()
        tag_counts.columns = ["Weighting_Tag_ID", "Count"]
 
        weights_per_tag = tag_counts.merge(
            tag_map_df[["Weighting_Tag_ID", "Weighting_Tag_Title"]],
            on="Weighting_Tag_ID",
            how="left"
        ).rename(columns={"Weighting_Tag_Title": "Weight Tag"})
 
        # Substances with Multiple Synonyms
        multi_synonym_substances = (
            source_df.groupby("(FK) Substance_ID")["Substance_Sourcing_Local_Name"]
            .count()
            .reset_index(name="Synonym Count")
            .query("`Synonym Count` > 1")
            .merge(ref_df, left_on="(FK) Substance_ID", right_on="Substance_Reference_ID", how="left")
            [["Substance_ID", "Substance_Name", "Synonym Count"]]
        ).sample(n=min(10, len(source_df)), random_state=1)
 
        # Substances with Only One Synonym
        single_synonym_substances = (
            source_df.groupby("(FK) Substance_ID")["Substance_Sourcing_Local_Name"]
            .count()
            .reset_index(name="Synonym Count")
            .query("`Synonym Count` == 1")
            .merge(ref_df, left_on="(FK) Substance_ID", right_on="Substance_Reference_ID", how="left")
            [["Substance_ID", "Substance_Name", "Synonym Count"]]
        ).sample(n=min(10, len(source_df)), random_state=1)
 
        # Calculate Synonym Count per Substance Type
        ref_with_type["Synonym Count"] = ref_with_type["Substance_Reference_ID"].map(
            combined_df.groupby("(FK) Substance_ID")["Substance_Sourcing_Local_Name"].count()
        )
 
        # Calculate Average Synonym Count per Type
        avg_synonym_count_per_type = (
            ref_with_type.groupby("Substance_Type_Title")["Synonym Count"]
            .mean()
            .reset_index(name="Synonym Count")
        )
 
        return {
            "substances_per_type": substances_per_type.replace([pd.NA, None, float('inf'), float('-inf')], "Not Available").to_dict(orient="records"),
            "top_synonyms": top_synonyms.replace([pd.NA, None, float('inf'), float('-inf')], "Not Available").to_dict(orient="records"),
            "weights_per_tag": weights_per_tag.replace([pd.NA, None, float('inf'), float('-inf')], "Not Available").to_dict(orient="records"),
            "multi_synonym_substances": multi_synonym_substances.replace([pd.NA, None, float('inf'), float('-inf')], "Not Available").to_dict(orient="records"),
            "single_synonym_substances": single_synonym_substances.replace([pd.NA, None, float('inf'), float('-inf')], "Not Available").to_dict(orient="records"),
            "avg_synonym_count_per_type": avg_synonym_count_per_type.replace([pd.NA, None, float('inf'), float('-inf')], "Not Available").to_dict(orient="records"),
            "multi_substance_synonyms": multi_substance_synonyms.to_dict(orient="records"),
            "single_substance_synonyms_count": int(single_substance_synonyms.shape[0]),
            "multi_substance_synonyms_count": int(multi_substance_synonyms.shape[0]),
            "ambiguous_top_10": top_ambiguous.to_dict(orient="records"),
            "total_synonyms": int(synonym_counts.shape[0]),
            "distribution": dist_df.to_dict(orient="records"),
            "top_substances_by_synonyms": top_substances.to_dict(orient="records")
 
            }
 
 
        
 
    except Exception as e:
        print("❌ Error in /synonyms:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    
 
 