# This is the file that implements a flask server to do inferences. It's the file that you will modify to
# implement the scoring for your own algorithm.

from __future__ import print_function

import os
import json
import pickle
import sys
import signal
import traceback
import flask
import io

import numpy as np

import pandas as pd
import torch

prefix = '/opt/ml/'
model_path = os.path.join(prefix, 'model')

# A singleton for holding the model. This simply loads the model and holds it.
# It has a predict function that does a prediction based on the model and the input data.

class ScoringService(object):
    model = None                # Where we keep the model when it's loaded

    @classmethod
    def get_model(cls):
        """Get the model object for this instance, loading it if it's not already loaded."""
        print('test get model -- test+1')
        if cls.model == None:
            #with open(os.path.join(model_path, 'decision-tree-model.pkl'), 'r') as inp:
        #    with open(os.path.join(model_path, 'best-LSTM-model-parameters.pkl'), 'rb') as inp:
        #       cls.model = pickle.load(inp)
            #the_model = torch.load(os.path.join(model_path, 'best-LSTM-model-parameters.pt'))
        #return cls.model
        
            cls.model = torch.jit.load(os.path.join(model_path, 'best-LSTM-model-parameters.pth'))
        
        return cls.model

    @classmethod
    def predict(cls, input):
        print('test predict')
        """For the input, do the predictions and return them.

        Args:
            input (a pandas dataframe): The data on which to do the predictions. There will be
                one prediction per row in the dataframe"""
        
        try:
            clf = cls.get_model()
        except:
            print('did not get the model')
        
        print('@@@@@@@@@@@@@@@@@@@')
        print(type(input))
        print(input)
        print(input[0])
        print(input[1])
        print('@@@@@@@@@@@@@@@@@@@')
        
        
        test_input=[[2779, 4496, 1744, 3480,  674,   24,   24,   24,   24,   24,   24,
          24,   24,   24,   24,   24,   24,   24,   24,   24,   24,   24,
          24,   24,   24,   24,   24,   24,   24,   24,   24,   24,   24,
          24,   24,   24,   24,   24,   24,   24,   24,   24,   24,   24,
          24,   24,   24,   24,   24,   24]]
        
        #return clf.predict(input)
        
        
        try:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            x=torch.from_numpy(np.array(input)).to(device)
        except Exception as error:
            print('Caught this error: ' + repr(error))
            print('error when generating input')
        
        try:
            with torch.no_grad():
                result = clf(x)
        except Exception as error:
            print('Caught this error: ' + repr(error))
            print('error when returing results for prediction')
            
        return result
    
# The flask app for serving predictions
app = flask.Flask(__name__)

@app.route('/ping', methods=['GET'])
def ping():
    """Determine if the container is working and healthy. In this sample container, we declare
    it healthy if we can load the model successfully."""
    print('testing ping()')
    health = ScoringService.get_model() is not None  # You can insert a health check here

    status = 200 if health else 404
    return flask.Response(response='\n', status=status, mimetype='application/json')

@app.route('/invocations', methods=['POST'])
def transformation():
    """Do an inference on a single batch of data. In this sample server, we take data as CSV, convert
    it to a pandas data frame for internal use and then convert the predictions back to CSV (which really
    just means one prediction per line, since there's a single column.
    """
    data = None
    print('testing transformation')
    # Convert from CSV to pandas
    if flask.request.content_type == 'text/csv':
        data = flask.request.data.decode('utf-8')
        s = io.StringIO(data)
        data = pd.read_csv(s, header=None)
    else:
        return flask.Response(response='This predictor only supports CSV data', status=415, mimetype='text/plain')

    
    print('#############')
    print('aaa')
    print('#############1')
    print(data)
    print('#############2')
    print(data[0])
    print('#############3')
    print(data.head() )
    print(type(data))
    print('############4')
    print('start')
    print(len(data[0]))
    for x in range(len(data[0])):
        print(x)
    
    print('aaa')
    print('Invoked with {} records'.format(data.shape[0]))

    # Do the prediction
    predictions = ScoringService.predict(data)
    
    print('*******')
    print(predictions)
    print('*******')
          
    # Convert from numpy back to CSV
    out = io.StringIO()
    pd.DataFrame({'results':predictions[0]}).to_csv(out, header=False, index=False)
    result = out.getvalue()

    return flask.Response(response=result, status=200, mimetype='text/csv')
