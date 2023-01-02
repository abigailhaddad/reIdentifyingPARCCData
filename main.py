# -*- coding: utf-8 -*-
"""

"""

#%pip install sympy
#%pip install openpxyl
#%pip install plotly
#%pip install plotnine

from sympy import symbols, Eq, solve, GreaterThan
import pandas as pd
import numpy as np
import os
import sympy
import numpy as np
from itertools import product
from string import ascii_lowercase
from fractions import Fraction
import plotnine
pd.options.mode.chained_assignment = None
"""
INPUTS: 
    
 '[5] 2021-22 School Level PARCC and MSAA Data edited.xlsx'
 with tabs: 
 "Proficiency"
Performance Level"

"[3] 2021-22 State Level PARCC and MSAA Data.xlsx"
with tabs 
 "Proficiency"
Performance Level"

OUTPUTS:
    "resultInitial.pkl" file with raw data in it
    
    
Technical Notes/Things That Came Up:
    
the solving here takes four parts:
    -'solving' total counts: this is the most basic part of the code -- we're basically just forward and backward filling missing Total Count data if there is a Total Count given for that school/level somewhere else in the data, or doing some addition'. 
    this is done in fillDf
    
    -taking advantage of the percent data given when count is missing to use fractions to solve for count: this is in 
    this is done via solveFractionWithDenominatorGetVar
    
    -using SymPy to substite missing values for equations, and using the various data relationships having to do with data aggregation to 'solve' the equations when possible
    this is in iterateThroughSchoolsSymbolsSolve
    
    -generating all of the possible remaining options and determining if for any of them, there's only one choice that works. some missing data can still get solved this way because SymPy doesn't really know how to use the fact that none of the values can be <0, so manually adding this constraint and
    iterating through all possible options can solve some of the remaining data
    this is in getSolvesOnes

the remaining code here evaluates the degree to which we were able to fill in missing values and tests code
    
-The two things that take up a lot of time for running this are:
    -making a lot of sympy symbols (even if you don't do anything with them but generate them)
    -generating and testing all the possible options to try to solve equations/variables we're not able to solve via Sympy (basically, iterating through all possible choices)
    
    the first issue, we control in the function replaceWithSymbolsAndGenerateEquations
    the line that controls the number of variables creates is AthroughD=[i for i in keywords if i[0]=="a" or i[0]=="b" or i[0]=="c" or i[0]=="d"]
    if you needed more variables, you'd go later in the alphabet. (for instance, if we wanted to add in functionality for looking at all the subgroup missing data, which this code currently drops)
    
    the second issue, we control via the maxSymbolsForIteration parameter. if you set that higher, it will attempt to solve (and in some cases, solve) unsolved count variables for schools with more data that's still unsolved after trying to solve it mathematically via
    sympy -- but because it's iterating through every possible option, if you set this higher, it will take a really long time to run -- much longer than everything ele combined'
    
"""
def filterInitialData():
    # we're only looking at rows in the data which meet these conditions
    filterDict={"Assessment Name": "PARCC",
               "Grade of Enrollment": "All",
               "Student group": "All"}
    return(filterDict)

def genMissingValues():
    # these are the values from Count and Total Count that we are going to replace with sympy symbols
    missingValues = ["n<10", "<=10%", "DS"]
    return(missingValues)

def genCleanSchool(schoolFile, tab):
    """
    This reads in a school data file, subsets it to just the rows we want based on the dictionary in filterInitialData, and returns that subset
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
    1) Takes a df with missing data for Count and Total Count (where missing can be DS, n<10, or <10%, as seen in genMissingValues)
    2) forward/backward fills when we have the missing numbers when we have them
    3) replaces fields that are still missing with -1s
    4) makes the count and total count fields into numbers
    5) if there are missing values in total count, ???
    
    """
    df=df.loc[df['Subject']=="ELA"]
    missingValues=genMissingValues()
    for value in missingValues:
        df[['Total Count', 'Count']]=df[['Total Count', 'Count']].replace(value, np.NaN)
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].ffill()
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].bfill()
    for schoolName in df['School Name'].unique():
        schoolData=df.loc[df['School Name']==schoolName]
        for j in schoolData['Metric Value'].unique():
            try:
                # this fill in some of the missing total count info
                metricData=schoolData.loc[(schoolData['Metric Value']==j)]
                nonAllMetricData=int(metricData[metricData['Tested Grade/Subject']!="All"]['Total Count'].values)
                if len([str(i) for i in  metricData if str(i)=="nan"])==1:
                    values=[int(i) for i in metricData  if str(i)!="nan"]
                    missing=nonAllMetricData-sum(values)
                    missingindex=df.loc[(df['School Name']==schoolName) & (df['Metric Value']==j) & (df['Total Count'].isnull())].index[0]
                    df.at[missingindex, 'Total Count']=missing    
            except:
                pass
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].ffill()
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].bfill()
    df=df.fillna(-1)
    df['Total Count']= pd.to_numeric(df['Total Count'], errors='coerce')
    df['Count'] = pd.to_numeric(df['Count'], errors='coerce')
    return(df[['Tested Grade/Subject', 'Metric Value', 'Count', 'Total Count', 'file', 'Percent','School Name']])

    
def solveFractionWithDenominatorGetVar(count, percent, total_count):
    # if we have a correct denominator (total_count), and we have a percent, and we have a missing count, this will return the correct numerator
    # if the percent and denominator are not consistent, this will return "Unexpected fraction result", which may break the rest of the code
    # but has not so far been an issue
    # this is kind of a hacky way of testing to see whether percent is actually a percent
    if count==-1 and  percent!=-1 and percent[0].isdigit():
        target=float(percent)/100
        denominator=total_count
        # this is returning something even when the numbers aren't correct
        lowest_possible=Fraction(int(round(target*denominator)), denominator)
        if round(lowest_possible.numerator/lowest_possible.denominator,2)!=round(target,2):
            return("Unexpected fraction result")
        elif lowest_possible.denominator==denominator:
            count=(lowest_possible.numerator)
        else:
            if denominator % lowest_possible.denominator==0:
                count=(denominator/lowest_possible.denominator * lowest_possible.numerator)  
    return(int(count))
    
def replaceWithSymbols(schoolData, mySymbols):   
    # this replaces -1s in Count and Total Count with sympy symbols that are unique to the school and the row #/column
    schoolData['Count']=schoolData.apply(lambda x: substituteSymbol(x['Count'], x['countWithinSchool'], mySymbols), axis=1)
    schoolData['Total Count']=schoolData.apply(lambda x: substituteSymbol(x['Total Count'], x['totalCountWithinSchool'], mySymbols), axis=1)
    schoolData=schoolData.drop(columns=['countWithinSchool', 'totalCountWithinSchool'])
    return(schoolData)

def substituteSymbol(value, valueWithinSchool, mySymbols):
    # this returns a symbol indexed at the valueWithinSchool if value is -1 ,and otherwise returns the value
    if value==-1:
        return(mySymbols[valueWithinSchool])
    else:
        return(value) 

def equationsByMetricFile(df, equationDict, number):
    # for each metric file (proficiency and All?) this sets up that the values where 'Tested Grade/Subject' is All is the sum of the non-All values
    # this adds each of those equations to the equationDict and returns it, along with the number for what number of equation we're on so that next equations don't write over any in the dictionary
    for i in list(df['Metric File'].unique()):
        number=number+1
        totalMetric=df.loc[(df['Metric File']==i) & (df['Tested Grade/Subject']=="All")]['Count'].iloc[0]
        myEquation=df.loc[(df['Metric File']==i) & (df['Tested Grade/Subject']!="All")]['Count'].values.sum()
        equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def equationsByTotalCountbyGrade(df, equationDict, number):
    nonProficientGrades= [i for i in list(df['Grade file'].unique()) if  "Proficiency" not in i]
    for i in nonProficientGrades:
        number=number+1
        # here we're saying, the total count in the levels (non-proficiency file) is the sum of the individual counts
        totalMetric=df.loc[df['Grade file']==i]['Total Count'].iloc[0]
        myEquation=df.loc[(df['Grade file']==i)]['Count'].values.sum()
        equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def equationsByProficientAndLevels(df, equationDict, number):
    for i in list(df.loc[df['file']=="Proficiency"]['Tested Grade/Subject'].unique()):
        # here we say: overall proficiency number is the sum of level 4 and 5
        number=number+1
        totalMetric=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']==i)]['Count'].iloc[0]
        myEquation=df.loc[(df['file']!="Proficiency") & (df['Tested Grade/Subject']==i) & df['Metric Value'].isin(["Performance Level 4", "Performance Level 5"])]['Count'].values.sum()
        equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def equationsWithinProficiency(df, equationDict, number):
    # here we're saying: within the proficiency file, the All is the sum of each grade
    number=number+1
    totalMetric=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']=="All")]['Count'].iloc[0]
    myEquation=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']!="All")]['Count'].values.sum()
    equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict)

def replaceWithSymbolsAndGenerateEquations(df, schoolNumber):
    # this generates symbols unique to each school (letters + schoolNumber), replaces the -1s in count and total count with those symbols, and then generates equations representing what we know about
    # the relationships between those numbers/variables
    keywords = [''.join(i) for i in product(ascii_lowercase, repeat = 2)] # you can make more symbols, but this is really what holds up the function and takes tons of time
    AthroughD=[i for i in keywords if i[0]=="a" or i[0]=="b" or i[0]=="c" or i[0]=="d"]
    myString=",".join(AthroughD)
    schoolString=myString.replace(",",f'{str(schoolNumber)},')+str(schoolNumber)
    mySymbols=symbols(schoolString, integer=True, nonnegative=True)
    number=0
    schoolData= replaceWithSymbols(df, mySymbols)
    equationDict={}
    equationDict, number=equationsByMetricFile(schoolData, equationDict, number)
    equationDict, number=equationsByTotalCountbyGrade(schoolData, equationDict, number)
    equationDict, number=equationsByProficientAndLevels(schoolData, equationDict, number)
    equationDict=equationsWithinProficiency(schoolData, equationDict, number)
    return(mySymbols, number, equationDict)

def symbolicSolveASchool(schoolData, schoolName, schoolNumber):
    mySymbols, number, equationDict=replaceWithSymbolsAndGenerateEquations(schoolData, schoolNumber)
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
    
def figureOutSums(symbolSolvedSet):
    # how many people do we know the grade and level for?
    byGrade=symbolSolvedSet.loc[(symbolSolvedSet['file']=="All") & (symbolSolvedSet['Tested Grade/Subject']!="All")]
    sumCountLevel=sum([i for i in list(byGrade['Count']) if type(i)==int])
    # how many people do we know the grade for?
    byAll=symbolSolvedSet.loc[(symbolSolvedSet['file']=="All") & (symbolSolvedSet['Tested Grade/Subject']=="All")]
    uniqueTotal=byAll.groupby(['Tested Grade/Subject', 'School Name']).first()['Total Count']
    sumCount=sum([i for i in uniqueTotal.values if type(i)==int])
    print([sumCountLevel, sumCount])
    
def testInitialComplete(resultInitial):
    byGrade=resultInitial.loc[(resultInitial['file']=="All") & (resultInitial['Tested Grade/Subject']!="All")]
    sumCountLevel=sum([i for i in list(byGrade['Count']) if i!=-1])
    byAll=resultInitial.loc[(resultInitial['file']=="All") & (resultInitial['Tested Grade/Subject']=="All")]
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
    resultInitial=fillDf(pd.concat([subsetProf, subsetAll]))
    resultInitial['countWithinSchool']=resultInitial.groupby(['School Name']).cumcount()+1
    maxCount=resultInitial['countWithinSchool'].max()
    resultInitial['totalCountWithinSchool']=resultInitial.groupby(['School Name']).cumcount()+maxCount    
    resultInitial['Metric File']=resultInitial['Metric Value']+resultInitial['file']
    resultInitial['Grade file']=resultInitial['Tested Grade/Subject']+resultInitial['file']
    return(resultInitial)

def genData():
    schoolFile='[5] 2021-22 School Level PARCC and MSAA Data edited.xlsx'
    schoolProficientTab="Proficiency"
    schoolLevelTab="Performance Level"
    subsetAll=cleanSchoolLevels(schoolFile, schoolLevelTab)
    subsetProf=cleanSchoolProficient(schoolFile, schoolProficientTab)
    subsetProf['Metric Value']="4 and 5"
    resultInitial=concatDatasets(subsetProf, subsetAll)
    resultInitial.to_pickle("resultInitial.pkl")  

def getOrGenData(generate=False):
    if generate==True:
        genData()
    try:
        resultInitial = pd.read_pickle("resultInitial.pkl") 
    except:
        genData()
    resultInitial = pd.read_pickle("resultInitial.pkl") 
    return(resultInitial)

def iterateThroughSchoolsSymbolsSolve(resultInitial):
    brokenSchools=[]
    fullListDF=[]
    schoolNumber=0
    schoolNames=list(resultInitial['School Name'].unique())
    for schoolName in schoolNames:  
        schoolData=resultInitial.loc[resultInitial['School Name']==schoolName]
        try:
            schoolData=symbolicSolveASchool(schoolData, schoolName, schoolNumber) 
        except:
            brokenSchools.append(schoolName)
        fullListDF.append(schoolData)
        schoolNumber=schoolNumber+1
    symbolSolvedSet=pd.concat(fullListDF)
    return(symbolSolvedSet, brokenSchools)

def genMetricsBySchool(resultInitial):
    metricsBySchool=[]
    for schoolName in resultInitial['School Name'].unique():
        schoolData=resultInitial.loc[resultInitial['School Name']==schoolName]
        count=len(schoolData)
        missingCount=count-len([i for i in schoolData['Count'].values if type(i)==int or i==-1])
        metricsBySchool.append([schoolName, count, missingCount])
    metricDF=pd.DataFrame(metricsBySchool, columns=['School', 'Line Count', 'Missing Count'])
    return(metricDF)

def determineNumberMissingSymbols(symbolSolvedSet):
    missingCounts=[]
    for schoolName in symbolSolvedSet['School Name'].unique():
    # this does not work FYI but also we don't really need it
        schoolData=symbolSolvedSet.loc[symbolSolvedSet['School Name']==schoolName]
        possibleValues=set([i for i in schoolData['Count'].values if type(i)!=int] + [i for i in schoolData['Total Count'].values if type(i)!=int])
        symbols=takeSymbolFromList(possibleValues)
        # this is not working becaus it's actually not the case the symbol is always there on its own
        missingCounts.append([schoolName, len(symbols)])
    dfmissing=pd.DataFrame(missingCounts)
    dfmissing.columns=['School Name', 'Count of Missing Symbols']
    return(dfmissing)

def testCombos(possibleValues, allCombos, unsolvedValues, myVars):
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
    
def takeSymbolFromList(unsolvedValues):
    firstPass=[i for i in unsolvedValues if type(i)==sympy.core.symbol.Symbol]
    unflatlist=[list(i._args) for i in unsolvedValues]
    secondPass=list(set([item for sublist in unflatlist for item in sublist if type(item)==sympy.core.mul.Mul or type(item)==sympy.core.symbol.Symbol]))
    firstAndSecond=firstPass+secondPass
    plusNegatives=firstAndSecond + [i * -1 for i in firstAndSecond]
    justPositives=list(set([i for i in plusNegatives if str(i)[0]!="-"]))
    return(justPositives)

def solveIfNMissing(symbolSolvedSet, schoolName):
    possibleValues=[]
    schoolData=symbolSolvedSet.loc[symbolSolvedSet['School Name']==schoolName]
    unsolvedValues=list(set([i for i in schoolData['Count'].values if type(i)!=int] + [i for i in schoolData['Total Count'].values if type(i)!=int] ))
    myVars=takeSymbolFromList(unsolvedValues)
    keepGoing=1
    for number in [i * 5 for i in range(1, 5)]:
        if keepGoing==1:
            allCombos=[i for i in product(range(0,number), repeat = len(myVars))]
            myVars, possibleValues=testCombos(possibleValues, allCombos, unsolvedValues, myVars)
            if len([i for i in possibleValues if number in i])<1 and len(possibleValues)>0:
                keepGoing=0
    if len(possibleValues)<1:
        print(f"hmm {schoolName}")
    return(myVars, possibleValues) 

def getSolvesOnes(symbolSolvedSet, dfmissing,  maxSymbolsForIteration):
    #this takes schools where there are still missing variables and iterates through their data and tries to solve the remaining symbols
    # the mechanism is that we know every value needs to be >=0; so this sometimes solves the equation
    # sympy is not good at using that inforamtion
    selectedSchools=dfmissing.loc[(dfmissing['Count of Missing Symbols']< maxSymbolsForIteration) & (dfmissing['Count of Missing Symbols']>0)]['School Name']
    dictOfReplacements={}
    listOfPossible=[]
    for schoolName in selectedSchools:
        myVars, possibleValues=solveIfNMissing(symbolSolvedSet, schoolName)
        schoolDF=pd.DataFrame(possibleValues, columns=myVars)
        listOfPossible.append(schoolDF)
    allPossible=pd.concat(listOfPossible)
    uniques=allPossible.nunique()
    justOneOption=uniques.loc[uniques==1]
    dfValues=allPossible[justOneOption.index]
    for col in dfValues.columns:
        value=[i for i in dfValues[col].values if str(i)!="nan"][0]
        dictOfReplacements[col]=value
    return(dictOfReplacements)

def applydict(value, dictOfReplacements):
    # this takes a value and if it's not an integer, tries to substitute a dictionary of symbol/value pairs into it
    if type(value)!=int:
        try:
            item=value.subs(dictOfReplacements)
            return(int(item))
        except:
            return(value)
    else:
        return(value)
    

os.chdir(r"C:\Users\aehaddad\Documents")

def main(generate=False, maxSymbolsForIteration=3):
    # generates (or loads) data
    initialDataSet=getOrGenData(generate)
    # solves what we can solve via using the percentages to find numerators
    initialDataSet['Count']=initialDataSet.apply(lambda x: solveFractionWithDenominatorGetVar(x['Count'], x['Percent'], x['Total Count']), axis=1)
    # generates symbols via sympy and solves what can be solved symbolically
    symbolSolvedSet, brokenSchools=iterateThroughSchoolsSymbolsSolve(initialDataSet)
    # determines how symbols are still missing per school
    dfmissing=determineNumberMissingSymbols(symbolSolvedSet)
    # iterates through to find solutions for the schools with less than maxSymbolsForIteration still missing
    dictOfReplacements=getSolvesOnes(symbolSolvedSet, dfmissing,  maxSymbolsForIteration)
    # applies the solutions for the variables which got solves
    symbolSolvedSet['Count']=symbolSolvedSet.apply(lambda x: applydict(x['Count'], dictOfReplacements), axis=1)     
    symbolSolvedSet['Total Count']=symbolSolvedSet.apply(lambda x: applydict(x['Total Count'], dictOfReplacements), axis=1)  
    return(symbolSolvedSet)


"""
number of people who we know their subject, level, and school
number of people who we know their subject, proficiency, and school
number of people who we know their level and school
number of people who we know their proficiency and school

same, but with symbols

"""

def getMetricsFromSubset(df):
    populated=[i for i in df['Count'] if i!=-1 and type(i)==int]
    populatedCount=len(populated)/len(df)
    populatedSum=sum(populated)
    return(populatedCount, populatedSum)
    
    
def getCounts(df):
    subjectAndLevel=df.loc[(df["file"]=="All") & (df["Tested Grade/Subject"]!="All")]
    subjectAndProficiency=df.loc[(df["file"]=="Proficiency") & (df["Tested Grade/Subject"]!="All")]
    level=df.loc[(df["file"]=="All") & (df["Tested Grade/Subject"]=="All")]
    proficiency=df.loc[(df["file"]=="Proficiency") & (df["Tested Grade/Subject"]=="All")]
    resultDict={"Subject and Level": getMetricsFromSubset(subjectAndLevel),
                "Subject and Proficient": getMetricsFromSubset(subjectAndProficiency),
                "Level":getMetricsFromSubset(level),
               "Proficient": getMetricsFromSubset(proficiency) }
    return(resultDict)


def aggregateCounts():
    # this kind of is a thing
    resultInitial=pd.DataFrame(getCounts(initialDataSet))
    resultInitial.index=["Populated Count", "Populated Sum"]
    resultFinal=pd.DataFrame(getCounts(symbolSolvedSet))
    resultFinal.index=["Populated Count", "Populated Sum"]
    initial=resultInitial.unstack().reset_index()
    initial['type']="Initial"
    final=resultFinal.unstack().reset_index()
    final['type']="Final"
    totalResult=pd.concat([initial, final])
    totalResult.columns=["Population", "Metric", "Count", "Type"]
    return(totalResult)


    
def genCleanState():
    """
    1) reads in the csv with state-level data as a df
    2) subsets it to just the populations we're interested in
    3) adds a 'file' column to show it came from the state data
    4) makes the count into a float
    """
    stateDict={"Assessment Name": "PARCC",
               "Student Group": "All",
               "Grade of Enrollment": "All"} 

    stateProficiencyData=pd.read_excel("[3] 2021-22 State Level PARCC and MSAA Data.xlsx", "Proficiency")
    stateLevelsData=pd.read_excel("[3] 2021-22 State Level PARCC and MSAA Data.xlsx", "Performance Level")
    
    for item in list(stateDict.keys()):
        stateProficiencyData=stateProficiencyData.loc[stateProficiencyData[item]==stateDict[item]]
        stateLevelsData=stateLevelsData.loc[stateLevelsData[item]==stateDict[item]]
        
    stateProficiencyData['Count']=stateProficiencyData['Count'].astype(float)
    stateLevelsData['Count']=stateLevelsData['Count'].astype(float)
    stateProficiencyData=stateProficiencyData[['Tested Grade/Subject', 'Count', 'Subject']]
    stateProficiencyData['file']="Proficient"
    stateLevelsData=stateLevelsData[['Tested Grade/Subject', 'Count', 'Subject', 'metric_value']]
    stateLevelsData['file']="Level"
    stateData=pd.concat([stateLevelsData, stateProficiencyData])
    return(stateData) 

def testSolveFractionWithDenominatorGetVar():
    # this tests the fraction-solving function
    df=pd.DataFrame(data={'Count': [-1, -1, -1, 3], 
                       'Percent': ["25.00", "28.57", "24.00", "75.00"],
                 "Total Count": [20, 7, 7, 4]})
    results=df.apply(lambda x: solveFractionWithDenominatorGetVar(x['Count'], x['Percent'], x['Total Count']), axis=1)
    if list(results.values)==[5, 2, 'Unexpected fraction result', 3]:
        print("SolveFractionWithDenominatorGetVar passed tests")
    else:
        print("SolveFractionWithDenominatorGetVar failed tests")



initialDataSet=getOrGenData()
symbolSolvedSet=main()

stateData= genCleanState()

stateCounts=stateData.loc[stateData['Tested Grade/Subject']=="All"].groupby(['Subject', 'file']).sum()[['Count']].reset_index()
stateCounts=stateCounts.rename(columns={"Count": "Total"})
totalResult=aggregateCounts()
populatedCount=totalResult.loc[totalResult['Metric']=="Populated Count"]
populatedSum=totalResult.loc[totalResult['Metric']=="Populated Sum"]


testSolveFractionWithDenominatorGetVar()

proficient=stateData.loc[stateData['file']=="Proficient"]
proficientELA=proficient.loc[proficient['Subject']=="ELA"][['Tested Grade/Subject', 'Count']]
"""
we want to incorporate state data, let's do the smallest set

"""
subjectAndProficiency=symbolSolvedSet.loc[(symbolSolvedSet["file"]=="Proficiency") & (symbolSolvedSet["Tested Grade/Subject"]!="All")]

nonIntValues=[i for i in subjectAndProficiency['Count'] if type(i)!=int]
solvedValues=subjectAndProficiency.loc[~subjectAndProficiency['Count'].isin(nonIntValues)]
solvedValues['Count']=solvedValues['Count'].astype(float)
countsWeHave=solvedValues.groupby('Tested Grade/Subject').sum()[['Count']]

mergedWithStateELA=countsWeHave.merge(proficientELA, left_index=True, right_on='Tested Grade/Subject')
mergedWithStateELA['Total Missing']=mergedWithStateELA['Count_y']-mergedWithStateELA['Count_x']

for grade in symbolSolvedSet['Tested Grade/Subject'].unique():
    if grade!="All":
        difference=mergedWithStateELA.loc[mergedWithStateELA['Tested Grade/Subject']==grade]['Total Missing']
        print(grade)
        print(difference.values[0])
        subset=symbolSolvedSet.loc[(symbolSolvedSet['Tested Grade/Subject']==grade) & (symbolSolvedSet['file']=="Proficiency")]
        missings=[i for i in subset['Count'] if type(i)!=int]
        print(missings)
        print()
        print()
        
    #grade 4 we're missing 12 students and it's all filled in?
    # so either something is incorrect in my code, or the data is wrong
    
grade="Grade 4"
grade4=initialDataSet.loc[(initialDataSet['Tested Grade/Subject']==grade) & (initialDataSet['file']=="Proficiency") ]
grade4solved=symbolSolvedSet.loc[(symbolSolvedSet['Tested Grade/Subject']==grade) & (symbolSolvedSet['file']=="Proficiency")]
# same length - we didn't lose any schools
initiallyMissingSchools=grade4.loc[grade4['Count']==-1]['School Name'].unique()
grade4solved.loc[grade4solved['School Name'].isin(initiallyMissingSchools)]

testOut=grade4solved.loc[grade4solved['School Name'].isin(initiallyMissingSchools)][['Count', 'Total Count', 'Percent']]
testOut['gen percent']=testOut['Count']/testOut['Total Count']
# these all look good
# the only possible wrong ones are the ones with <s
# and those look good too
# could those be 12 bigger?
possibly=testOut.loc[testOut["Percent"].str.contains("<")]
# 