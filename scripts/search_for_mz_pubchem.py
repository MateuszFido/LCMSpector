import pubchempy as pcp
import logging
import json

logging.basicConfig(level=logging.DEBUG)


def main():
    list_of_compounds = [
        "12-Oxochenodeoxycholic Acid",
        "12-Oxolithocholic Acid",
        "2-Methylbutyrate",
        "3-Aminoisobutyrate",
        "3-Deoxycholic Acid",
        "3-Oxocholic Acid",
        "3-Oxodeoxycholic Acid",
        "3-Oxolithocholic Acid",
        "4-Methylvalerate",
        "5-Aminovalerate",
        "7-Oxodeoxycholic Acid",
        "Acetate",
        "Alanine",
        "Allocholic Acid",
        "Alloisolithocholic Acid",
        "Allolithocholic Acid",
        "Alpha-Muricholic Acid",
        "Anthranilic Acid",
        "Aspartate",
        "Beta-Muricholic Acid",
        "Biotin",
        "Butyrate",
        "Chenodeoxycholic Acid",
        "Cholic Acid",
        "Crotonate",
        "Cysteine",
        "Deoxycholic Acid",
        "Desaminotyrosine",
        "Folate",
        "Gamma-Muricholic Acid",
        "Glutamate",
        "Glycine",
        "Glycochenodeoxycholic Acid",
        "Glycocholic Acid",
        "Glycodehydrocholic Acid",
        "Glycodeoxycholic Acid",
        "Glycohyodeoxycholic Acid",
        "Glycolithocholic Acid",
        "Glycoursodeoxycholic Acid",
        "Hexanoate",
        "Hyodeoxycholic Acid",
        "Indole",
        "Indole-3-Acetamide",
        "Indole-3-Acetate",
        "Indole-3-Acrylate",
        "Indole-3-Carboxaldehyde",
        "Indole-3-Lactate",
        "Indole-3-Propionate",
        "Indole-3-Pyruvate",
        "Isobutyrate",
        "Isodeoxycholic Acid",
        "Isoleucine",
        "Isolithocholic Acid",
        "Isovalerate",
        "Itaconate",
        "Kynurenic Acid",
        "Kynurenine",
        "Leucine",
        "Lithocholic Acid",
        "Lysine",
        "Methionine",
        "Methylserotonin",
        "N-Acetylserotonin",
        "Niacin",
        "Omega-Muricholic Acid",
        "P-Cresol",
        "Palmitate",
        "Pantothenic Acid",
        "Phenol",
        "Phenylalanine",
        "Picolinic Acid",
        "Pyridoxal Phosphate",
        "Proline",
        "Propionate",
        "Quinolinic Acid",
        "Serine",
        "Succinate",
        "Taurochenodeoxycholic Acid",
        "Taurocholic Acid",
        "Taurodeoxycholic Acid",
        "Taurohyodeoxycholic Acid",
        "Taurolithocholic Acid",
        "Tauroursodeoxycholic Acid",
        "Threonine",
        "Trans-Indole-3-Acrylate",
        "Tryptamine",
        "Tryptophan",
        "Tryptophol",
        "Tyramine",
        "Tyrosine",
        "Ursodeoxycholic Acid",
        "Valerate",
        "Valine",
    ]

    PROTON_MASS = 1.007276

    ion_list_name = {}

    for item in list_of_compounds:
        result = pcp.get_properties(["IUPACName", "ExactMass"], item, namespace="name")
        if not result:
            print(f"Not found: {item}")
            continue
        rec = result[0]
        exact_mass = float(rec["ExactMass"])
        if exact_mass is None:
            print(f"No exact mass found for {item}")
            continue
        mz_pos = round(exact_mass + PROTON_MASS, 4)
        mz_neg = round(exact_mass - PROTON_MASS, 4)

        info_mz1 = "[M+H]+"
        info_mz2 = "[M-H]-"

        ion_list_name[item] = {"ions": [mz_pos, mz_neg], "info": [info_mz1, info_mz2]}

        with open("ion_list.json", "w", encoding="utf-8") as f:
            json.dump({"ion_list_name": ion_list_name}, f, indent=2)


if __name__ == "__main__":
    main()
