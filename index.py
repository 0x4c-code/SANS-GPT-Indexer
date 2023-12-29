import os
import pdfplumber
from dotenv import load_dotenv
import openai
import pandas as pd
from collections import defaultdict
import time

# Load .env file
load_dotenv()

# Extract variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PDF_PASSWORD = os.getenv('PDF_PASSWORD')

# Adjust to the name of the course and whatever you want to name the files
PDF_PATH='/home/savagehack/SANS_Auto_Indexer/SEC5885.pdf'
outfile='SEC5885.csv'

# Set openai key
openai.api_key = OPENAI_API_KEY

# Initialize the data structure
index = defaultdict(lambda: {'pages': set(), 'definition': ''})

# Open the PDF
with pdfplumber.open(PDF_PATH, password=PDF_PASSWORD) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        print(f'prompting for page {i}...\n')  # Just to see it's working

        # Prepare the prompt
        prompt = f"I'll be providing you one page from a SANS book at a time, and I want you identify the most important term or concept on the page as it relates to Cloud, Cybsercurity, and Threat Detection, in order to create an index of the book. Some pages may not have an imporant term or phrase at all, especially pages that are just title pages or don't have much content, in these cases just say none. Please ensure the terms are concise, relevant and key to the page's content. Each page should have at most a single term identified. List the term along with a short (5-15) word definition for the term, separated by a comma, with no addittional text. The selected terms should be concrete concepts or succinct phrases of no more than 3-4 words at most, and only if the term is discussed in-depth on that page, and not simply mentioned in passing. Avoid phrases that are complex or overly descriptive, such as 'Logged in during a likely password spray'. Exclude people's names (I.e. Your Name, and the authors of the book), anything about page numbers or licensing, the course title (SECXXX Course Title), and any terms that are too generic or broad. If a term is a MITRE ATT&CK technique, include only the T-code and the short name of the technique, not 'MITRE ATT&CK'. Here is the next page: \n\n{text}"

        try:
            # OpenAI API call
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=prompt,
                max_tokens=150
            )

            # Parse the response
            for line in response.choices[0].text.split('\n'):
                if line and line.lower().replace('.', '') != 'none':
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        term, definition = parts
                        term = term.strip().replace('"', '').replace("'", '')
                        definition = definition.strip()

                        index[term]['pages'].add(i)
                        if not index[term]['definition']:
                            index[term]['definition'] = definition
                    else:
                        print(f"Unexpected format in response: '{line}'")

        except openai.error.RateLimitError as e:
            print("Rate limit exceeded. Waiting before retrying...")
            time.sleep(60)  # Sleep for 60 seconds before retrying

# Convert the data into a pandas DataFrame
df = pd.DataFrame(
    [(term, ', '.join(map(str, sorted(data['pages']))), data['definition']) for term, data in index.items()],
    columns=['Term', 'Pages', 'Definition']
)

# Save it as a CSV
print("converting to CSV...\n")
df.to_csv(outfile, index=False)
