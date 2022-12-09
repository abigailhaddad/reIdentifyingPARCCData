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

"""
INPUTS: 
    
"schoolevel1.csv"
"schoolevel2.csv"
"stateLevel.csv"

 '[5] 2021-22 School Level PARCC and MSAA Data edited.xlsx'
"""

def getNumberVariablesLeft(solved):
    stuff=[ ''.join(filter(str.isalpha, str(i))) for i in list(solved.values())]
    length=len(list(set([i for i in stuff if len(i)>0])))
    return(length)

def genCleanState(stateFile):
    """
    1) reads in the csv with state-level data as a df
    2) subsets it to just the populations we're interested in
    3) adds a 'file' column to show it came from the state data
    4) makes the count into a float
    """

    stateData=pd.read_csv(stateFile)
    stateDict={"Assessment Name": "PARCC",
               "Student Group": "All",
               "Grade of Enrollment": "All"}
    for item in list(stateDict.keys()):
        stateData=stateData.loc[stateData[item]==stateDict[item]]
    stateData['file']="State"
    stateData['Count']=stateData['Count'].astype(float)
    return(stateData) 

def genCleanSchool(schoolFile, tab):
    """
    This reads in a school data file, subsets it to just the rows we want, and returns that subset
    """
    schoolData=pd.read_excel(schoolFile, tab)
    schoolDict={"Assessment Name": "PARCC",
           "Grade of Enrollment": "All",
           "Student group": "All"}
    subset=schoolData
    for item in list(schoolDict.keys()):
        subset=subset.loc[subset[item]==schoolDict[item]]
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
    df=df.loc[df['Subject']=="ELA"]
    df=df.replace("n<10","DS")
    df=df.replace("<=10%", "DS")
    df=df.replace("DS",np.NaN)
    df['Total Count']=df.groupby('Tested Grade/Subject')['Total Count'].ffill()
    df['Total Count']=df.groupby('Tested Grade/Subject')['Total Count'].bfill()
    df.sort_values(['Tested Grade/Subject'])
    df=df.fillna(-1)
    df['Total Count']= pd.to_numeric(df['Total Count'], errors='coerce')
    df['Count'] = pd.to_numeric(df['Count'], errors='coerce')
    return(df[['Tested Grade/Subject', 'Metric Value', 'Count', 'Total Count', 'file', 'Percent','School Name']])


def intermediate(subsetAll,subsetProf,  schoolName):
    """
    

    Parameters
    ----------
    subsetAll : DF
        this is the school level data
    subsetProf : DF
       this is the school proficiency data
    schoolName : string
        this is the name of the school we want data for

    Returns
    -------
    boths : DF
        this is the subset of the school level and proficiency data just for the school named

    """
    sampleSchool=subsetAll.loc[subsetAll['School Name']==schoolName]
    sampleProf=subsetProf.loc[subsetProf['School Name']==schoolName]
    sampleProf['Metric Value']="4 and 5"
    boths=fillDf(pd.concat([sampleSchool, sampleProf]))
    return(boths)


def replaceWithSymbols(df, mySymbols, number):
    for i in range(0, len(df)):
        if df['Count'].iloc[i]==-1:
            df['Count'].iloc[i]=mySymbols[number]
            number=number+1
        if df['Total Count'].iloc[i]==-1:
            df['Total Count'].iloc[i]=mySymbols[number]
            number=number+1
    if number==0:
       print(f'no missings in {schoolName}')
    return(df, mySymbols, number)
 
    
def whatIsThisDoing(df, number):
    equationDict={}
    number=0
    for i in list(df['Metric File'].unique()):
        # this is the sum of whatever metric we are looking at
        totalMetric=df.loc[(df['Metric File']==i) & (df['Tested Grade/Subject']=="All")]['Count'].iloc[0]
        # these are the disaggregated values
        otherItems=df.loc[(df['Metric File']==i) & (df['Tested Grade/Subject']!="All")]
        othervalues=otherItems['Count'].values
        # here we're saying, the total metric is equal to the sum of the disaggregated values
        myEquation=0
        for j in range(0, len(othervalues)):
            myEquation += othervalues[j]
        # this adds an equation to the dictionary that's the sum of the individual piees equals the totalMetric
        equationDict[number]= Eq((myEquation), totalMetric)
        number=number+1
    return(equationDict, number)

def whatIsThisOtherThingDoing(df, equationDict, number):
    for i in list(df['Grade file'].unique()):
        if "Proficiency" not in i:
            # here we're saying, the total count in the levels (non-proficiency file) is the sum of the individual counts
            totalMetric=df.loc[df['Grade file']==i]['Total Count'].iloc[0]
            othervalues=df.loc[(df['Grade file']==i)]['Count'].values
            myEquation=0
            for j in range(0, len(othervalues)):
                myEquation += othervalues[j]
            equationDict[number]= Eq((myEquation), totalMetric)
            number=number+1
    return(equationDict, number)

def finalWhatThing(df, equationDict, number):
    for i in list(df.loc[df['file']=="Proficiency"]['Tested Grade/Subject'].unique()):
        # here we say: overall proficiency number is the sum of level 4 and 5
        totalMetricsLine=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']==i)]
        totalMetric=totalMetricsLine['Count'].iloc[0]
        otherValues=df.loc[(df['file']!="Proficiency") & (df['Tested Grade/Subject']==i)]
        otherValues=otherValues.loc[otherValues['Metric Value'].isin(["Performance Level 4", "Performance Level 5"])]['Count'].values
        myEquation=0
        for j in range(0, len(otherValues)):
            myEquation += otherValues[j]
        equationDict[number]= Eq((myEquation), totalMetric)
        number=number+1
    return(equationDict)


def allsClean(df, schoolNumber):
    """
    

    Parameters
    ----------
    df : df
        this is the school and level description for a school
    schoolNumber : int
        this is a number between 1 and n, where n is the number of schools

    Returns
    -------
    Symbols now used for this school, number of ? equations? , dictionary of equations for the school

    """
    myString='a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z,aa,ab,ac,ad,ae,af,ag,ah,ai,aj,ak,al,am,an,ao,ap,aq,ar,as,at,au,av,aw,ax,ay,az,aaa,aab,aac,aad,aae,aaf,aag'
    schoolString=myString.replace(",",f'{str(schoolNumber)},')+str(schoolNumber)
    mySymbols=symbols(schoolString, integer=True, nonnegative=True)
    df['Metric File']=df['Metric Value']+df['file']
    df['Grade file']=df['Tested Grade/Subject']+df['file']
    number=0
    df, mySymbols, number= replaceWithSymbols(df, mySymbols, number)
    equationDict, number=whatIsThisDoing(df, number)
    equationDict, number=whatIsThisOtherThingDoing(df, equationDict, number)
    equationDict=finalWhatThing(df, equationDict, number)
    """
    subsetProf=df.loc[df['file']=="Proficiency"]
    totalMetric=subsetProf.loc[subsetProf['Tested Grade/Subject']=='All']['Total Count'].iloc[0]
    otherValues=subsetProf.loc[subsetProf['Tested Grade/Subject']!='All']['Total Count'].values
    for j in range(0, len(otherValues)):
        myEquation += otherValues[j]
    equationDict[number]= Eq((myEquation), totalMetric)
    number=number+1
    """
    return(mySymbols, number, equationDict)


def allForSchool(subsetAll,subsetProf, schoolName, schoolNumber):
    """
    

    Parameters
    ----------
    subsetAll : df
        DESCRIPTION.
    subsetProf : df
        DESCRIPTION.
    schoolName : string
        DESCRIPTION.
    schoolNumber : int
        DESCRIPTION.

    Returns
    -------
    boths: df with symbols, solved when possible

    """
    boths=intermediate(subsetAll,subsetProf, schoolName)
    initialBoths=boths[['Tested Grade/Subject', 'Metric Value', 'Count']]
    mySymbols, number, equationDict=allsClean(boths, schoolNumber)
    numberOfRealEquations=len([i for i in list(equationDict.values()) if i!=True])
    if numberOfRealEquations>0:
        allequations=tuple(equationDict.values())
        solved=(solve((allequations), (mySymbols)))
        for item in list(solved.keys()):
            toReplace=solved[item]
            try:
                toReplace=int(toReplace)
                #if schoolName=="Sela PCS":
                #    print([schoolName, item, toReplace])
                #print(toReplace)
                # some of these are actually pretty big - like, bigger than 10
                # so if we want to use this to say <10 for missings
                # we need to distinguish between DS and <10 and see which is which
            except:
                pass
            boths=boths.replace(item,toReplace)
  
        totalVars=len([i for i in list(solved.values())])
        unsolvedVars=len([i for i in list(solved.values()) if type(i)==sympy.core.add.Add])
        toAppend=[schoolName, totalVars, unsolvedVars]
        numberUnsolved=getNumberVariablesLeft(solved)
        #print(toAppend)
        print([schoolName, numberUnsolved])
        #return(toAppend) ## OK there we go 
        boths['School Name']=schoolName 
        return(boths)
    else:
        boths['School Name']=schoolName
        return(boths)
    
def figureOutSums(fullDF):
    # how many people do we know the grade and level for?
    byGrade=fullDF.loc[(fullDF['file']=="All") & (fullDF['Tested Grade/Subject']!="All")]
    sumCountLevel=sum([i for i in list(byGrade['Count']) if type(i)==int])
    # how many people do we know the grade for?
    byAll=fullDF.loc[(fullDF['file']=="All") & (fullDF['Tested Grade/Subject']=="All")]
    uniqueTotal=byAll.groupby(['Tested Grade/Subject', 'School Name']).first()['Total Count']
    sumCount=sum([i for i in uniqueTotal.values if type(i)==int])
    print([sumCountLevel, sumCount])
    
def testInitialComplete(subsetAll, subsetProf):
    """
    

    Parameters
    ----------
    subsetAll : df
        DESCRIPTION.
    subsetProf : df
        DESCRIPTION.

    Returns
    -------
    prints the sum of the students where we know what level they are, and the sum where we know what school they go to

    """
    bothsAll=fillDf(pd.concat([subsetAll, subsetProf]))
    byGrade=bothsAll.loc[(bothsAll['file']=="All") & (bothsAll['Tested Grade/Subject']!="All")]
    sumCountLevel=sum([i for i in list(byGrade['Count']) if i!=-1])
    byAll=bothsAll.loc[(bothsAll['file']=="All") & (bothsAll['Tested Grade/Subject']=="All")]
    uniqueTotal=byAll.groupby(['Tested Grade/Subject', 'School Name']).first()['Total Count']
    sumCount=sum([i for i in uniqueTotal.values if i!=-1])
    #print([sumCountLevel, sumCount])
    # sumCOuntLevel is working, sumCount is not  -ot's overreporting
  

def allPlusState(fullDF, stateData):
    # this doesnt't seem to solve anything! 
    symbols=[]
    equationDict={}
    number=0
    fullAll=fullDF.loc[fullDF['file']=="All"]
    stateData=stateData.loc[stateData['Subject']=="ELA"]
    for i in list(stateData['Tested Grade/Subject'].unique()):
        for j in list(stateData['metric_value'].unique()):
            totalMetric=stateData.loc[(stateData['Tested Grade/Subject']==i) & (stateData['metric_value']==j)].iloc[0]['Count']
            otherValuesLine=fullAll.loc[(fullAll['Tested Grade/Subject']==i) & (fullAll['Metric Value']==j)]
            symbols=symbols+getSymbols(otherValuesLine)
            otherValues=otherValuesLine['Count'].sum()
            myEquation=0
            equationDict[number]= Eq((otherValues), int(totalMetric)) # something weird
            number=number+1
    allequations=tuple(equationDict.values())
    solved=(solve((allequations), (symbols)))
    return(solved)

def getSymbols(otherValuesLine):
    args=[ i.args for i in otherValuesLine['Count'] if type(i)!=int]
    symbols=[i for i in list(sum(args, ())) if  type(i)==sympy.core.symbol.Symbol]            
    symbols=symbols+([i*-1 for i in list(sum(args, ())) if  type(i)==sympy.core.mul.Mul])
    return(symbols)


os.chdir(r"C:\Users\aehaddad\Documents")

schoolFile='[5] 2021-22 School Level PARCC and MSAA Data edited.xlsx'
schoolProficientTab="Proficiency"
schoolLevelTab="Performance Level"
stateFile="stateLevel.csv" 
    
    
stateData=genCleanState(stateFile)    
subsetAll=cleanSchoolLevels(schoolFile, schoolLevelTab)
subsetProf=cleanSchoolProficient(schoolFile, schoolProficientTab)
testInitialComplete(subsetAll, subsetProf)
schoolNames=list(subsetAll['School Name'].unique())
fullListDF=[]
fullList=[]
schoolNumber=0

for schoolName in schoolNames:
    try:
        boths=allForSchool(subsetAll,subsetProf, schoolName, schoolNumber)
        toAppend=[schoolName, "not broke", "not broke"] # this was supposed to be numbers
    except:
        toAppend=[schoolName, "broke", "broke"]
        #print(toAppend)
    fullListDF.append(boths)
    fullList.append(toAppend)
    schoolNumber=schoolNumber+1
myDF=pd.DataFrame(fullList)
nonBroke=myDF.loc[myDF[1]!="broke"]
#print(nonBroke.mean()) # this is because we have this toappend stuff
#print(len(myDF)-len(nonBroke))
#print(1-nonBroke.mean()[2]/nonBroke.mean()[1])
fullDF=pd.concat(fullListDF)

totalELA=42999    
#which schools do we still not have counts for?
byAll=fullDF.loc[(fullDF['file']=="All") & (fullDF['Tested Grade/Subject']=="All")]
s=byAll['Total Count']
nonMissingIndex=s[s.apply(lambda x: isinstance(x, int))].index
byAll.loc[~byAll.index.isin(nonMissingIndex)]


figureOutSums(fullDF)
"""
42999-42287 # this seems too big for just four smaller schools 

Performance Level 1	11626
Performance Level 2	8838
Performance Level 3	9320
Performance Level 4	10122
Performance Level 5	3093

this is ELA - do we see differences in proportions accounted for?


# these are the schools we don't have numbers for

list(byAll.loc[~byAll.index.isin(nonMissingIndex)]['School Name'].unique())


['Maya Angelou PCS - Academy at DC Jail',
 'Goodwill Excel Center PCS',
 'I Dream PCS',
 'Maya Angelou Academy @ Youth Services Center',
 'Maya Angelou Academy at New Beginnings formerly Oak Hill']

#we're filtering here again for numbers

s=byAll['Count']
nonMissingIndex=s[s.apply(lambda x: isinstance(x, int))].index
byAll.loc[byAll.index.isin(nonMissingIndex)]
byAll.loc[byAll.index.isin(nonMissingIndex)].groupby('Metric Value').sum()['Count']

#we're overwhelmginly missing 2s - we have +98%+ of our 4s, 3s, and 1s - 
# so we actually might be able to figure out stuff


# figuring out another method
i='English II'
j='Performance Level 5'
totalMetric=stateData.loc[(stateData['Tested Grade/Subject']==i) & (stateData['metric_value']==j)].iloc[0]['Count']
otherValuesLine=fullAll.loc[(fullAll['Tested Grade/Subject']==i) & (fullAll['Metric Value']==j)]
symbols=getSymbols(otherValuesLine)
otherValues=otherValuesLine['Count'].sum()
from sympy.solvers.diophantine import diophantine
from sympy.solvers.diophantine.diophantine import diop_solve
"""

"""
example:

-g - i + 10 > -1
5 - g > -1
g - 1 > -1
11 - i > -1
i - 8 > -1

g>-1
i>-1


i  - 10 - i + 10  == 0
5 + i - 10 == i - 5
9 - i 
11 - i 
i - 8 






from sympy import *
g, i= symbols("g, i", integer=True, nonnegative=True)
list_of_inequalities = [-g - i + 10, 5 - g, g - 1 , 11 - i, i - 8]

sols = [solve(t, g)[0] for t in list_of_inequalities if g in S(t).free_symbols]

sols = [solveset(t >= 0, g, S.Reals) for t in list_of_inequalities if g in S(t).free_symbols]



remaining=[i for i in list(boths['Count']) if type(i)!=int]

for item in range(0, len(initialBoths)):
    if initialBoths['Count'].iloc[item]==-1:
        if type(boths['Count'].iloc[item])==int:
            print(initialBoths.iloc[item])
            print(boths.iloc[item][['Count']])
            print()
"""


def genAllSubgroup(schoolFile, tab):
    """
    This reads in a school data file, subsets it to just the rows we want, and returns that subset
    """
    schoolData=pd.read_excel(schoolFile, tab)
    schoolDict={"Assessment Name": "PARCC",
           "Grade of Enrollment": "All"}
    subset=schoolData
    for item in list(schoolDict.keys()):
        subset=subset.loc[subset[item]==schoolDict[item]]
    return(subset)


allSubgroup=genAllSubgroup(schoolFile, schoolLevelTab)
allSubgroup['file']="school_levels_subgroup"
allSubgroupfill=fillDf(allSubgroup)
allSubgroupfill['Subgroup Value']=allSubgroup['Subgroup Value']
allSubgroupfill['Subject']=allSubgroup['Subject']

for school in allSubgroupfill['School Name'].unique():
    subsetSchool=allSubgroupfill.loc[allSubgroupfill["School Name"]==school]
    for grade in subsetSchool['Tested Grade/Subject'].unique():
        subsetGrade=subsetSchool.loc[subsetSchool['Tested Grade/Subject']==grade]
        for value in subsetGrade['Metric Value'].unique():
            subsetValue=subsetGrade.loc[subsetGrade['Metric Value']==value]
            for subject in subsetValue['Subject'].unique():
                subsetSubject=subsetValue.loc[subsetValue['Subject']==subject]
                if subsetSubject.loc[subsetSubject['Subgroup Value']=="All"]['Count'].iloc[0]==-1:
                    otherValues=list(subsetSubject.loc[subsetSubject['Subgroup Value']!="All"]['Count'].values)
                    if len([i for i in otherValues if i!=-1])>0:
                        print([school, grade, value, subject])
