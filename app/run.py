import nltk
import json
import joblib
import plotly
import argparse
import pandas as pd

from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

from flask import Flask
from flask import render_template, request, jsonify
from plotly.graph_objs import Bar, Histogram
from sqlalchemy import create_engine

from sklearn.base import BaseEstimator,TransformerMixin

parser = argparse.ArgumentParser(description='Run web app')
parser.add_argument('database_filepath', type=str, help='Path to database')
parser.add_argument('model_filepath', type=str, help='Path to saved model')
args = parser.parse_args()    


class StartingVerbExtractor(BaseEstimator, TransformerMixin):
    """
    Custom transformer class that checks if the sentence starts with a verb
    """
    def starting_verb(self, text):
        """
        Checks if the starting word of text is a verb
        Input:
            text: Input text
        Output:
            True if starting word in text is a verb else False
        """
        sentence_list = nltk.sent_tokenize(text)
        for sentence in sentence_list:
            pos_tags = nltk.pos_tag(tokenize(sentence))
            first_word, first_tag = pos_tags[0]
            if first_tag in ['VB', 'VBP'] or first_word == 'RT':
                return True
        return False

    def fit(self, x, y=None):
        return self

    def transform(self, X):
        """
        Apply transform. Overloaded function.
        Input:
            X: input text data
        Output:
            Input text data transformed by `starting_verb`
        """
        X_tagged = pd.Series(X).apply(self.starting_verb)
        return pd.DataFrame(X_tagged)


def tokenize(text):
    tokens = word_tokenize(text)
    lemmatizer = WordNetLemmatizer()

    clean_tokens = []
    for tok in tokens:
        clean_tok = lemmatizer.lemmatize(tok).lower().strip()
        clean_tokens.append(clean_tok)

    return clean_tokens


app = Flask(__name__)


# load data
engine = create_engine(f'sqlite:///{args.database_filepath}')
df = pd.read_sql_table('disaster_data', engine)

# load model
model = joblib.load(f"{args.model_filepath}")


# index webpage displays cool visuals and receives user input text for model
@app.route('/')
@app.route('/index')
def index():
    
    # Graph 1 -- Category sum
    category_sum = df.drop(["message", "id", "original", "genre"], axis=1).sum() 
    category_names = list(category_sum.index)
    
    # Graph 2 -- Message length
    df["message_len"] = df["message"].apply(lambda x: len(tokenize(x)))

    # create visuals
    graphs = [
        {
            'data': [
                Bar(
                    x=category_names,
                    y=category_sum
                )
            ],

            'layout': {
                'title': 'Total Sum for Each Category',
                'yaxis': {
                    'title': "Sum"
                },
                'xaxis': {
                    'title': "Category"
                }
            }
        },
        {
            'data': [
                Histogram(
                    x=df["message_len"]
                )
            ],

            'layout': {
                'title': 'Message Length Histogram',
                'yaxis': {
                    'title': "Message Length"
                },
                'xaxis': {
                    'title': "Bins"
                }
            }
        }        
    ]
    
    # encode plotly graphs in JSON
    ids = ["graph-{}".format(i) for i, _ in enumerate(graphs)]
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)

    # render web page with plotly graphs
    return render_template('master.html', ids=ids, graphJSON=graphJSON)


# web page that handles user query and displays model results
@app.route('/go')
def go():
    # save user input in query
    query = request.args.get('query', '') 

    # use model to predict classification for query
    classification_labels = model.predict([query])[0]
    classification_results = dict(zip(df.columns[4:], classification_labels))

    # This will render the go.html Please see that file. 
    return render_template(
        'go.html',
        query=query,
        classification_result=classification_results
    )


def main():
    app.run(host='0.0.0.0', port=3001, debug=True)


if __name__ == '__main__':
    main()