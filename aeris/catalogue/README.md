# AERIS product catalogue (Ebola response)

Builds the Africa CDC product catalogue for AERIS from the logistics team's commodity lists, with French names,
and the files used to import it. 516 distinct items: treatment-centre lists (medicines, medical devices, PPE,
WASH & logistics, blood transfusion, intensive care), IPC kits for health facilities and safe and dignified burials.
Together with the 32 products received first, AERIS holds 542 `ACDC-` products (imported live on 2 November 2026).

## Files

| File | What it is |
| --- | --- |
| `source/List_of_commodities_for_AERIS.zip` | The logistics team's three Excel lists, as received |
| `catalogue_master.json` | One row per distinct item: code, category, English name, unit, source lists, IPC unit cost |
| `tr_out_1.json` … `tr_out_3.json` | French names and points to check, per code |
| `source/AERIS_catalogue_review_revised_GB.xlsx` | The logistics review (GB) of the review workbook |
| `apply_review.py` | Reads a reviewed workbook, tidies units and typos, writes `review_overrides.json` |
| `review_overrides.json` | Reviewed English name, French name and unit per code (applied by the build) |
| `refdata/live/2_products.csv` | The 32 products already in AERIS before the catalogue |
| `build_catalogue.py` | Writes the review workbook for logistics and the three import files |
| `catalogue_import/` | `1_categories.xlsx`, `Ebola 2026.csv` (products), `3_synonyms.xlsx` (French names) |
| `test_catalogue_import.py` | Imports those files into the **local test copy** (localhost) as the test admin |

## Codes and rules

- Codes continue the first products: `ACDC-MED`, `EQP`, `IPC`, `WSH`, `LAB`, `ICU`, `SDB`, `COM` + 3 digits.
  Six catalogue items that are identical to products already received keep the existing code.
- Units are bilingual (`tablet / comprimé`, `bag / poche`): the unit stock is counted in.
- Lot and expiry are required at receipt for medicines, laboratory, PPE and burial items; not for equipment,
  WASH or intensive care.
- The products file is named `Ebola 2026.csv` on purpose: the product import tags every product with the file name,
  and "Ebola 2026" is the existing tag.
- Categories are plain English names (a `|fr:` French variant breaks the product import and some React screens).
  Starlink kits and phones go in **Telecommunication** (renamed from "Telecom / ICT" on 2 November 2026).

## After a new review

```
python apply_review.py <reviewed workbook.xlsx>
python build_catalogue.py <new review workbook to send back.xlsx>
python test_catalogue_import.py          # local copy only; add --skip-categories when they already exist
```

Then import the three files on the live site in this order: categories (Configuration → Import data → Category),
products (Products → Import products, the CSV), French names (Import data → Product Synonyms). Re-importing products
updates them by code; delete the old French names first or they are doubled.

## Known gaps

- Unit costs (32 IPC items, from the IPC list) are in the CSV but were left out of the live import: a product import
  with costs needs the Finance role.
- Open questions for logistics: accents removed from 13 French drug names in the review; 6 flagged items (MED-120,
  MED-134, EQP-073, IPC-035, WSH-013, WSH-096); 7 possible duplicates of the first products, kept separate for now.
- The step that turned the three Excel lists into `catalogue_master.json` was done interactively; the master file is
  the record of that step.
