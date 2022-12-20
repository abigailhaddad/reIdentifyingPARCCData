# -*- coding: utf-8 -*-
"""
Spyder Editor

Functionality I want:
    clean up all this stuff
    tell me we solved something - how many things did we solve via what?
    is it ever the case that they tell us something from a subgroup that they didn't from the main group?'
    show the percentage solved

This is a temporary script file.
"""

#%pip install sympy
#%pip install openpxyl

from sympy import symbols, Eq, solve, GreaterThan
import pandas as pd
import numpy as np
import os
import sympy
pd.options.mode.chained_assignment = None
import numpy as np

from itertools import product
from string import ascii_lowercase


"""
INPUTS: 
    
"schoolevel1.csv"
"schoolevel2.csv"

 '[5] 2021-22 School Level PARCC and MSAA Data edited.xlsx'
"""
def filterInitialData():
    filterDict={"Assessment Name": "PARCC",
               "Grade of Enrollment": "All",
               "Student group": "All"}
    return(filterDict)

def genMissingValues():
    missingValues = ["n<10", "<=10%", "DS"]
    return(missingValues)

def getNumberVariablesLeft(solved):
    stuff=[ ''.join(filter(str.isalpha, str(i))) for i in list(solved.values())]
    length=len(list(set([i for i in stuff if len(i)>0])))
    return(length)

def genCleanSchool(schoolFile, tab):
    """
    This reads in a school data file, subsets it to just the rows we want, and returns that subset
    """
    schoolData=pd.read_excel(schoolFile, tab)
    filterDict=filterInitialData()
    subset=schoolData
    for item in list(filterDict.keys()):
        subset=subset.loc[subset[item]==filterDict[item]]
    return(subset)

def cleanSchoolProficient(schoolFile, schoolProficientTab):
    """
    This cleans the 'proficiency numbers by school file'
    """
    schoolProficientData=genCleanSchool(schoolFile, schoolProficientTab)
    schoolProficientData['file']="Proficiency"
    colsToKeep=['School Name', 'Subject', 'Tested Grade/Subject', 'Count', 'Total Count', 'file', 'Percent']
    return(schoolProficientData[colsToKeep])
    
def cleanSchoolLevels(schoolFile, schoolLevelTab):
    """
    This cleans the 'level numbers by school file'
    """
    schoolLevelData=genCleanSchool(schoolFile, schoolLevelTab)
    schoolLevelData['file']="All"
    colsToKeep=['School Name', 'Subject', 'Tested Grade/Subject', 'Metric Value', 'Count', 'Total Count', 'file', 'Percent']
    return(schoolLevelData[colsToKeep])
    
def fillDf(df):

    """
    1) Takes a df with missing data (where missing can be DS, n<10, or <10%)
    2) forward/backward fills when we have the missing numbers when we have them
    3) replaces fields that are still missing with -1s
    4) makes the count and total count fields into numbers
    
    """
    df=df.loc[df['Subject']!="ELA"]
    missingValues=genMissingValues()
    for value in missingValues:
        df=df.replace(value, np.NaN)
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].ffill()
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].bfill()
    for schoolName in df['School Name'].unique():
        subset=df.loc[df['School Name']==schoolName]
        for j in subset['Metric Value'].unique():
            try:
                smaller=subset.loc[(subset['Metric Value']==j)]
                alls=int(smaller.loc[smaller['Tested Grade/Subject']=="All"]['Total Count'].iloc[0])
                smalls=smaller.loc[smaller['Tested Grade/Subject']!="All"]['Total Count'].values
                if len([str(i) for i in smalls if str(i)=="nan"])==1:
                    values=[int(i) for i in smalls  if str(i)!="nan"]
                    missing=alls-sum(values)
                    missingindex=df.loc[(df['School Name']==schoolName) & (df['Metric Value']==j) & (df['Total Count'].isnull())].index[0]
                    df.at[missingindex, 'Total Count']=missing    
            except:
                print(schoolName)
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].ffill()
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].bfill()
    df=df.fillna(-1)
    df['Total Count']= pd.to_numeric(df['Total Count'], errors='coerce')
    df['Count'] = pd.to_numeric(df['Count'], errors='coerce')
    return(df[['Tested Grade/Subject', 'Metric Value', 'Count', 'Total Count', 'file', 'Percent','School Name']])

def replaceWithSymbols(schoolData, mySymbols):    
    schoolData['Count']=schoolData.apply(lambda x: substituteSymbol(x['Count'], x['countWithinSchool'], mySymbols), axis=1)
    schoolData['Total Count']=schoolData.apply(lambda x: substituteSymbol(x['Total Count'], x['countWithinSchool'], mySymbols), axis=1)
    schoolData=schoolData.drop(columns=['countWithinSchool', 'totalCountWithinSchool'])
    return(schoolData)

def substituteSymbol(count, countWithinSchool, mySymbols):
    if count==-1:
        return(mySymbols[countWithinSchool])
    else:
        return(count) 
    
def whatIsThisDoing(df, equationDict, number):
    for i in list(df['Metric File'].unique()):
        number=number+1
        totalMetric=df.loc[(df['Metric File']==i) & (df['Tested Grade/Subject']=="All")]['Count'].iloc[0]
        myEquation=df.loc[(df['Metric File']==i) & (df['Tested Grade/Subject']!="All")]['Count'].values.sum()
        equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def whatIsThisOtherThingDoing(df, equationDict, number):
    nonProficientGrades= [i for i in list(df['Grade file'].unique()) if  "Proficiency" not in i]
    for i in nonProficientGrades:
        number=number+1
        # here we're saying, the total count in the levels (non-proficiency file) is the sum of the individual counts
        totalMetric=df.loc[df['Grade file']==i]['Total Count'].iloc[0]
        myEquation=df.loc[(df['Grade file']==i)]['Count'].values.sum()
        equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def sumRelationships():
    inCommon='Grade file'
    total={"file": "All",
          "value": "Total Count"}
    count={"file": "All",
           "value": "Count"}
    return(inCommon, total, count)

def finalWhatThing(df, equationDict, number):
    for i in list(df.loc[df['file']=="Proficiency"]['Tested Grade/Subject'].unique()):
        # here we say: overall proficiency number is the sum of level 4 and 5
        number=number+1
        totalMetric=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']==i)]['Count'].iloc[0]
        myEquation=df.loc[(df['file']!="Proficiency") & (df['Tested Grade/Subject']==i) & df['Metric Value'].isin(["Performance Level 4", "Performance Level 5"])]['Count'].values.sum()
        equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)


def proficiencySumByGrade(df, equationDict, number):
    number=number+1
    totalMetric=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']=="All")]['Count'].iloc[0]
    myEquation=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']!="All")]['Count'].values.sum()
    equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict)

def allsClean(df, schoolNumber):
    keywords = [''.join(i) for i in product(ascii_lowercase, repeat = 2)] # you can make more symbols, but this is really what holds up the function and takes tons of time
    AandB=[i for i in keywords if i[0]=="a" or i[0]=="b"]
    myString=",".join(AandB)
    schoolString=myString.replace(",",f'{str(schoolNumber)},')+str(schoolNumber)
    mySymbols=symbols(schoolString, integer=True, nonnegative=True)
    number=0
    schoolData= replaceWithSymbols(df, mySymbols)
    equationDict={}
    equationDict, number=whatIsThisDoing(schoolData, equationDict, number)
    equationDict, number=whatIsThisOtherThingDoing(schoolData, equationDict, number)
    equationDict, number=finalWhatThing(schoolData, equationDict, number)
    equationDict=proficiencySumByGrade(schoolData, equationDict, number)
    return(mySymbols, number, equationDict)

def allForSchool(schoolData, schoolName, schoolNumber):
    mySymbols, number, equationDict=allsClean(schoolData, schoolNumber)
    valuesInSchoolData=list(schoolData['Count'].values)+list(schoolData['Total Count'].values)
    symbolsWeUse=[i for i in valuesInSchoolData if type(i)== sympy.core.symbol.Symbol]
    mySymbols=tuple([i for i in mySymbols if i in symbolsWeUse])
    # the length of this is the length of initially missing things
    numberOfRealEquations=len([i for i in list(equationDict.values()) if i!=True])
    if numberOfRealEquations>0:
        allequations=tuple(equationDict.values())
        solved=(solve((allequations), (mySymbols)))
        for item in list(solved.keys()):
            toReplace=solved[item]
            try:
                toReplace=int(toReplace)
            except:
                pass
            schoolData=schoolData.replace(item,toReplace)
        return(schoolData)
    else:
        schoolData['School Name']=schoolName
        return(schoolData)
    
def figureOutSums(fullDF):
    # how many people do we know the grade and level for?
    byGrade=fullDF.loc[(fullDF['file']=="All") & (fullDF['Tested Grade/Subject']!="All")]
    sumCountLevel=sum([i for i in list(byGrade['Count']) if type(i)==int])
    # how many people do we know the grade for?
    byAll=fullDF.loc[(fullDF['file']=="All") & (fullDF['Tested Grade/Subject']=="All")]
    uniqueTotal=byAll.groupby(['Tested Grade/Subject', 'School Name']).first()['Total Count']
    sumCount=sum([i for i in uniqueTotal.values if type(i)==int])
    print([sumCountLevel, sumCount])
    
def testInitialComplete(levelsAndProf):

    byGrade=levelsAndProf.loc[(levelsAndProf['file']=="All") & (levelsAndProf['Tested Grade/Subject']!="All")]
    sumCountLevel=sum([i for i in list(byGrade['Count']) if i!=-1])
    byAll=levelsAndProf.loc[(levelsAndProf['file']=="All") & (levelsAndProf['Tested Grade/Subject']=="All")]
    uniqueTotal=byAll.groupby(['Tested Grade/Subject', 'School Name']).first()['Total Count']
    sumCount=sum([i for i in uniqueTotal.values if i!=-1])
    print([sumCountLevel, sumCount])
    # sumCOuntLevel is working, sumCount is not  -ot's overreporting
  

def getSymbols(otherValuesLine):
    args=[ i.args for i in otherValuesLine['Count'] if type(i)!=int]
    symbols=[i for i in list(sum(args, ())) if  type(i)==sympy.core.symbol.Symbol]            
    symbols=symbols+([i*-1 for i in list(sum(args, ())) if  type(i)==sympy.core.mul.Mul])
    return(symbols)

def concatDatasets(subsetProf, subsetAll):
    levelsAndProf=fillDf(pd.concat([subsetProf, subsetAll]))
    levelsAndProf['countWithinSchool']=levelsAndProf.groupby(['School Name']).cumcount()+1
    maxCount=levelsAndProf['countWithinSchool'].max()
    levelsAndProf['totalCountWithinSchool']=levelsAndProf.groupby(['School Name']).cumcount()+maxCount    
    levelsAndProf['Metric File']=levelsAndProf['Metric Value']+levelsAndProf['file']
    levelsAndProf['Grade file']=levelsAndProf['Tested Grade/Subject']+levelsAndProf['file']
    return(levelsAndProf)

def genData():
    schoolFile='[5] 2021-22 School Level PARCC and MSAA Data edited.xlsx'
    schoolProficientTab="Proficiency"
    schoolLevelTab="Performance Level"
    subsetAll=cleanSchoolLevels(schoolFile, schoolLevelTab)
    subsetProf=cleanSchoolProficient(schoolFile, schoolProficientTab)
    subsetProf['Metric Value']="4 and 5"
    levelsAndProf=concatDatasets(subsetProf, subsetAll)
    levelsAndProf.to_pickle("levelsAndProf.pkl")  

def getOrGenData(gen=False):
    if gen==True:
        genData()
    try:
        levelsAndProf = pd.read_pickle("levelsAndProf.pkl") 
    except:
        genData()
    levelsAndProf = pd.read_pickle("levelsAndProf.pkl") 
    return(levelsAndProf)

os.chdir(r"C:\Users\aehaddad\Documents")

levelsAndProf=getOrGenData(gen=False)
testInitialComplete(levelsAndProf)
brokenSchools=[]

fullListDF=[]
schoolNumber=0

schoolNames=list(levelsAndProf['School Name'].unique())

for schoolName in schoolNames:  
    schoolData=levelsAndProf.loc[levelsAndProf['School Name']==schoolName]
    try:
        schoolData=allForSchool(schoolData, schoolName, schoolNumber) 
    except:
        brokenSchools.append(schoolName)
    fullListDF.append(schoolData)
    schoolNumber=schoolNumber+1

fullDF=pd.concat(fullListDF)
figureOutSums(fullDF)
#print(fullDF.loc[fullDF['School Name']=="Sela PCS"]['Count'])
schoolData=fullDF.loc[fullDF['School Name']=="Sela PCS"]

def genMetricsBySchool(levelsAndProf):
    metricsBySchool=[]
    for schoolName in levelsAndProf['School Name'].unique():
        schoolData=levelsAndProf.loc[levelsAndProf['School Name']==schoolName]
        count=len(schoolData)
        missingCount=count-len([i for i in schoolData['Count'].values if type(i)==int or i==-1])
        metricsBySchool.append([schoolName, count, missingCount])
    metricDF=pd.DataFrame(metricsBySchool, columns=['School', 'Line Count', 'Missing Count'])
    return(metricDF)

initialCount=genMetricsBySchool(levelsAndProf)
print(initialCount['Missing Count'].sum())
finalCount=genMetricsBySchool(fullDF)
print(finalCount['Missing Count'].sum())

missingCounts=[]
for schoolName in fullDF['School Name'].unique():
    # this does not work FYI but also we don't really need it
    #schoolName="Sela PCS"
    sample=fullDF.loc[fullDF['School Name']==schoolName]
    symbols=set([i for i in sample['Count'].values if type(i)==sympy.core.symbol.Symbol])
    missingCounts.append([schoolName, len(symbols)])

dfmissing=pd.DataFrame(missingCounts)
dfmissing.columns=['School Name', 'Count of Missing Symbols']

def solveIfNMissing(fullDF, schoolName):
    possibleValues=[]
    sample=fullDF.loc[fullDF['School Name']==schoolName]
    unsolvedValues=[i for i in sample['Count'].values if type(i)!=int]
    myVars=list(set([i for i in unsolvedValues if type(i)==sympy.core.symbol.Symbol]))
    allCombos=[i for i in product(range(0,20), repeat = len(myVars))]
    for aSet in allCombos:
        values=[]
        dictionaryOfValues={}
        for count in range(0, len(myVars)):
            dictionaryOfValues[myVars[count]]=aSet[count] # this is working
        for item in unsolvedValues:
            value=item.subs(dictionaryOfValues)
            values.append(value)
        if all(x >= 0 for x in values):
            possibleValues.append(aSet)
    return(myVars, possibleValues) 

def getSolvesOnes(fullDF, dfmissing):
    selectedSchools=dfmissing.loc[dfmissing['Count of Missing Symbols']<3]['School Name']
    # this takes awhile to run
    dictOfReplacements={}
    for schoolName in selectedSchools:
        myVars, possibleValues=solveIfNMissing(fullDF, schoolName)
        if len(possibleValues)==1:
            replacements=possibleValues[0]
            for item in range(0, len(myVars)):
                dictOfReplacements[myVars[item]]=replacements[item]       
    return(dictOfReplacements)

dictOfReplacements=getSolvesOnes(fullDF, dfmissing)

def applydict(nonintvalue, dictOfReplacements):
    if type(nonintvalue)!=int:
        try:
            item=nonintvalue.subs(dictOfReplacements)
            return(int(item))
        except:
            return(nonintvalue)
    else:
        return(nonintvalue)
    
figureOutSums(fullDF)

# of new ones we filled in 

fullDF['Test Count']=fullDF.apply(lambda x: applydict(x['Count'], dictOfReplacements), axis=1)     
byGrade=fullDF.loc[(fullDF['file']=="All") & (fullDF['Tested Grade/Subject']!="All")]
print(sum([i for i in list(byGrade['Test Count']) if type(i)==int])-sum([i for i in list(byGrade['Count']) if type(i)==int]))



# so we are getting slghtly more

# it's working



"""
        #totalVars=len([i for i in list(solved.values())])
        #unsolvedVars=len([i for i in list(solved.values()) if type(i)==sympy.core.add.Add])
        #toAppend=[schoolName, totalVars, unsolvedVars]
        #numberUnsolved=getNumberVariablesLeft(solved)
        #schoolData['School Name']=schoolName 
        
        
['Maya Angelou PCS - Academy at DC Jail',
 'Goodwill Excel Center PCS',
 'I Dream PCS',
 'Maya Angelou Academy @ Youth Services Center',
 'Maya Angelou Academy at New Beginnings formerly Oak Hill']

#we're filtering here again for numbers
#we're overwhelmginly missing 2s - we have +98%+ of our 4s, 3s, and 1s - 
# so we actually might be able to figure out stuff



def sumsToAll():
    sumsToAll=[["White/Caucasian", 
           "Hispanic/Latino",
           "Two or More Races",
           "Black/African American",
           "American Indian/Alaska Native",
           "Asian",
           "Pacific Islander/Native Hawaiian"],
           ["Military Connected",
            "Not Military Connected"],
           ["Not At-Risk",
            "At-Risk"],
           ["Not an English Learner",
            "English Learner"],
           ["Not Homeless",
            "Homeless"],
           ["CFSA",
            "Not CFSA"],
           ["Not Active or Monitored English Learner",
            "Active or Monitored English Learner"],
           ["Students with Disabilities",
            "Not Special Education"]]
    return(sumsToAll)




# let's get into ranges!




def solveIfOneMissing(fullDF, schoolName):
    possibleValues=[]
    sample=fullDF.loc[fullDF['School Name']==schoolName]
    unsolvedValues=[i for i in sample['Count'].values if type(i)!=int]
    myVar=[i for i in unsolvedValues if type(i)==sympy.core.symbol.Symbol][0]
    try:
        for i in range(0,50):
            values=[]
            for item in range(0, len(unsolvedValues)):
                value=unsolvedValues[item].subs({myVar: i})
                values.append(value)
            if all(x >= 0 for x in values):
                possibleValues.append(i)
        return(possibleValues)        
    except:
        print(schoolName)






 
for schoolName in justOnes:
    print(schoolName)
    values=(solveIfOneMissing(fullDF, schoolName))
    print(len(values))
    
    
for schoolName in fullDF['School Name'].unique():
    print(schoolName)
    values=solveIfNMissing(fullDF, schoolName)
    print(len(values))
    
for schoolName in justOnes:
    firstWay=(solveIfOneMissing(fullDF, schoolName))
    secondWay=solveIfNMissing(fullDF, schoolName)
    if len(firstWay)==len(secondWay):
        print([schoolName, "yay"])
    else:
        print([schoolName, "nooo"])
    
# a fair number of these only have one variable unsolved for
schoolName= 'Benjamin Banneker High School'



# can we figure out anything about algebra?
geometryValues=fullDF.loc[fullDF['Grade file']=="GeometryProficiency"][['School Name', 'Count', 'Total Count']]



integers=[i for i in geometryValues['Count'].values if type(i)==int]
sum(integers)

"""