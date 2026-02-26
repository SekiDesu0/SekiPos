import pandas as pd
import json
import os

file_path = os.getcwd() + 'PLU+FSMA+list+v1.0.xlsx'
sheet_name = 'Non FTL' 
new_url_base = "https://server-ifps.accurateig.com/assets/commodities/"

def get_one_of_each():
    if not os.path.exists(file_path):
        print("❌ Excel file not found.")
        return

    # 1. Load Excel
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # 2. Drop rows missing the essentials
    df = df.dropna(subset=['IMAGE', 'PLU', 'COMMODITY'])

    # 3. CRITICAL: Drop duplicates by COMMODITY only
    # This ignores Variety and Size, giving us exactly one row per fruit type.
    df_unique = df.drop_duplicates(subset=['COMMODITY'], keep='first')

    data_output = []

    for _, row in df_unique.iterrows():
        # Extract filename from the messy URL in Excel
        original_link = str(row['IMAGE'])
        filename = original_link.split('/')[-1]
        
        # Build the final working URL
        image_url = f"{new_url_base}{filename}"
        
        # Get the clean Commodity name
        commodity = str(row['COMMODITY']).title()
        plu_code = str(row['PLU'])

        data_output.append({
            "name": commodity,
            "plu": plu_code,
            "image": image_url
        })

    # 4. Save to JSON
    with open('one_of_each.json', 'w', encoding='utf-8') as f:
        json.dump(data_output, f, indent=4, ensure_ascii=False)

    print(f"✅ Success! Generated 'one_of_each.json' with {len(data_output)} unique commodities.")

if __name__ == "__main__":
    get_one_of_each()
