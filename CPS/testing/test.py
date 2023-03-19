import pandas as pd
import numpy as np
import math
import datetime as dt

import matplotlib.pyplot as plt
from itertools import cycle
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, explained_variance_score, r2_score 
from sklearn.metrics import mean_poisson_deviance, mean_gamma_deviance, accuracy_score
from sklearn.preprocessing import MinMaxScaler

from pyodide.http import open_url





lData = open_url("https://raw.githubusercontent.com/Infihnity3/CPS/main/historical-price/BTC-USD.csv")
data=pd.read_csv(lData)

data = data.rename(columns={'Date': 'date','Open':'open','High':'high','Low':'low','Close':'close',
                                'Adj Close':'adj_close','Volume':'volume'})

data['date'] = pd.to_datetime(data.date)

y_2022 = data.loc[(data['date'] >= '2022-01-01')
                    & (data['date'] < '2023-01-01')]

y_2022.drop(y_2022[['adj_close','volume']],axis=1)

monthv= y_2022.groupby(y_2022['date'].dt.strftime('%B'))[['open','close']].mean()
new_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 
            'September', 'October', 'November', 'December']
monthv = monthv.reindex(new_order, axis=0)

closedp = data[['date','close']]

closedp = closedp[closedp['date'] > '2020-01-01']
closed = closedp.copy()

del closedp['date']
scaler=MinMaxScaler(feature_range=(0,1))
closedp=scaler.fit_transform(np.array(closedp).reshape(-1,1))

trainingSize=int(len(closedp)*0.70)
testSize=len(closedp)-trainingSize
trainData,testData=closedp[0:trainingSize,:],closedp[trainingSize:len(closedp),:1]

def createdata(dataset, time_step=1):
    dataX, dataY = [], []
    for i in range(len(dataset)-time_step-1):
        a = dataset[i:(i+time_step), 0]   
        dataX.append(a)
        dataY.append(dataset[i + time_step, 0])
    return np.array(dataX), np.array(dataY)

time_step = 21
X_train, y_train = createdata(trainData, time_step)
X_test, y_test = createdata(testData, time_step)

model = XGBRegressor(n_estimators=1000)
model.fit(X_train, y_train, verbose=False)

prediction = model.predict(X_test)

trainPredict=model.predict(X_train)
testPredict=model.predict(X_test)

trainPredict = trainPredict.reshape(-1,1)
testPredict = testPredict.reshape(-1,1)

trainPredict = scaler.inverse_transform(trainPredict)
testPredict = scaler.inverse_transform(testPredict)
original_ytrain = scaler.inverse_transform(y_train.reshape(-1,1)) 
original_ytest = scaler.inverse_transform(y_test.reshape(-1,1)) 

look_back=time_step
plotTrain = np.empty_like(closedp)
plotTrain[:, :] = np.nan
plotTrain[look_back:len(trainPredict)+look_back, :] = trainPredict

plotTest = np.empty_like(closedp)
plotTest[:, :] = np.nan
plotTest[len(trainPredict)+(look_back*2)+1:len(closedp)-1, :] = testPredict

names = cycle(['Original close price','Train predicted close price','Test predicted close price'])

plotdf = pd.DataFrame({'date': closed['date'],
                    'original_close': closed['close'],
                    'train_predicted_close': plotTrain.reshape(1,-1)[0].tolist(),
                    'test_predicted_close': plotTest.reshape(1,-1)[0].tolist()})

x_input=testData[len(testData)-time_step:].reshape(1,-1)
temp_input=list(x_input)
temp_input=temp_input[0].tolist()

from numpy import array

lst_output=[]
n_steps=time_step
i=0
prediction_days = 60
while(i<=prediction_days):    
    if(len(temp_input)>time_step):
        
        x_input=np.array(temp_input[1:])
        #print("{} day input {}".format(i,x_input))
        x_input=x_input.reshape(1,-1)
        
        yhat = model.predict(x_input)
        #print("{} day output {}".format(i,yhat))
        temp_input.extend(yhat.tolist())
        temp_input=temp_input[1:]
    
        lst_output.extend(yhat.tolist())
        i=i+1
        
    else:
        yhat = model.predict(x_input)
        
        temp_input.extend(yhat.tolist())
        lst_output.extend(yhat.tolist())
        
        i=i+1
        
last_days=np.arange(1,time_step+1)
day_pred=np.arange(time_step+1,time_step+prediction_days+1)

temp_mat = np.empty((len(last_days)+prediction_days+1,1))
temp_mat[:] = np.nan
temp_mat = temp_mat.reshape(1,-1).tolist()[0]

last_original_days_value = temp_mat
next_predicted_days_value = temp_mat

last_original_days_value[0:time_step+1] = scaler.inverse_transform(closedp[len(closedp)-time_step:]).reshape(1,-1).tolist()[0]
next_predicted_days_value[time_step+1:] = scaler.inverse_transform(np.array(lst_output).reshape(-1,1)).reshape(1,-1).tolist()[0]

new_pred_plot = pd.DataFrame({
    'last_original_days_value':last_original_days_value,
    'next_predicted_days_value':next_predicted_days_value
})

names = cycle(['Last 15 days close price','Predicted next 10 days close price'])

model=closedp.tolist()
model.extend((np.array(lst_output).reshape(-1,1)).tolist())
model=scaler.inverse_transform(model).reshape(1,-1).tolist()[0]

names = cycle(['Close Price'])

fig, ax = plt.subplots()
plt.plot(model,ls='solid')
plt.legend(['Closing Price'])
plt.title('Prediction of Closing Price for Bitcoin-USD')
plt.xlabel('Days')
plt.ylabel('Price')
ax.set_facecolor("#202b38")

pyscript.write("plot",fig)
