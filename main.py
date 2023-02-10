from sympy import symbols, Eq, solve
import pandas as pd
import os
import sympy
from itertools import product
from string import ascii_lowercase
from fractions import Fraction
pd.options.mode.chained_assignment = None
import numpy as np
import numbers

def filterInitialData():
    """This produces a dictionary of the column - value pairs we want to keep

    Returns:
      filterDict: a dictionary of the column - value pairs we want to keep

    """
    filterDict={"Assessment Name": "PARCC",
               "Grade of Enrollment": "All",
               "Student group": "All"}
    return(filterDict)

def genMissingValues():
    """This produces a list of the strings that mean missing values

    Returns:
      missingValues: a list of the strings in the value columns that mean the data has been redacted

    """
    missingValues = ["n<10", "<=10%", "DS"]
    return(missingValues)

def genFilterSchool(schoolFile, tab):
    """This reads in an Excel tab and filters the data to return a subset of it

    Args:
      schoolFile: string indicating the name of an xlsx file
      tab: string indicating the tab name in that file

    Returns:
      subset: a pandas df that has been filtered via a dictionary with field names and values

    """
    schoolData=pd.read_excel(schoolFile, tab)
    filterDict=filterInitialData()
    subset=schoolData
    for item in list(filterDict.keys()):
        subset=subset.loc[subset[item]==filterDict[item]]
    return(subset)

def filterDropCols(schoolFile, schoolTab, columnValue):
    """This filters the school data, adds a column indicating whether it's levels or proficiency data, and drops unneeded columns

    Args:
      schoolFile: string indicating the name of an xlsx file
      schoolTab: string indicating a tab name in that file 
      columnValue: string indicating whether this is proficiency or levels data

    Returns:
      subsetCols: a pandas df that has been filtered via a dictionary with field names and values, and with only selected columns

    """
    schoolData=genFilterSchool(schoolFile, schoolTab)
    schoolData['file']=columnValue
    colsToKeep=['Subject',
     'Count',
     'Percent',
     'Metric Value',
     'Total Count',
     'Tested Grade/Subject',
     'file',
     'School Name']
    subsetCols=schoolData[[i for i in colsToKeep if i in schoolData.columns]]
    return(subsetCols)
    
def fillDf(df, subject):
    
    """This takes the combined levels and proficiency data and does some cleaning
    1) replaces strings indicating missingness with NaN
    2) uses forward fill and backward fill to populate Total Count when we have it for the same School Name/Tested Grade/Subject combo
    3) does some additional total count filling-in
    4) replaces remaining NaNs with -1
    5) Makes Count and Total Count into numeric
    6) Returns the pandas dataframe with just certain columns
    Args:
      df: data frame
      subject: string for Math or ELA

    Returns:
      cleanedDF: the pandas df with steps 1-6 done to it

    """
    df=df.loc[df['Subject']==subject]
    missingValues=genMissingValues()
    for value in missingValues:
        df[['Total Count', 'Count']]=df[['Total Count', 'Count']].replace(value, np.NaN)
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].ffill()
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].bfill()
    for schoolName in df['School Name'].unique():
        schoolData=df.loc[df['School Name']==schoolName]
        for j in schoolData['Metric Value'].unique():
            try:
                # this fills in some of the missing total count info
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
    cleanedDF=df[['Tested Grade/Subject', 'Metric Value', 'Count', 'Total Count', 'file', 'Percent','School Name']]
    return(cleanedDF)
    
def solveFractionWithDenominatorGetVar(count, percent, total_count):
    
    """This takes a count, percent, and total_count and if the count is missing but we have the percent and total_count will return the count

    Args:
      count: -1 if missing, a non-negative integer otherwise
      percent: -1 if missing, a non-negative float otherwise
      total_count: -1 if missing, a non-negative integer otherwise

    Returns:
      result: "Unexpected fraction result" if something broke, the count if the count was already non-missing, and the (solved) count if it was solved
      """
    if count==-1 and  percent!=-1 and percent[0].isdigit():
        target=float(percent)/100
        denominator=total_count
        lowest_possible=Fraction(int(round(target*denominator)), denominator)
        if round(lowest_possible.numerator/lowest_possible.denominator,2)!=round(target,2):
            result="Unexpected fraction result"
            return(result)
        elif lowest_possible.denominator==denominator:
            count=(lowest_possible.numerator)
        else:
            if denominator % lowest_possible.denominator==0:
                count=(denominator/lowest_possible.denominator * lowest_possible.numerator)  
    result=int(count)
    return(result)
    
def replaceWithSymbols(schoolData, mySymbols):   
        
    """This takes the data, subset by school, and replaces the -1s with SymPy symbols

    Args:
      schoolData: pandas DF of the subset of data by School Name
      mySymbols: list of SymPy symbols
     
    Returns:
      schoolDataSymbols:  pandas DF of the subset of data by School Name with SymPy symbols for missing numbers
      """
    schoolData['Count']=schoolData.apply(lambda x: substituteSymbol(x['Count'], x['countWithinSchool'], mySymbols), axis=1)
    schoolData['Total Count']=schoolData.apply(lambda x: substituteSymbol(x['Total Count'], x['totalCountWithinSchool'], mySymbols), axis=1)
    schoolDataSymbols=schoolData.drop(columns=['countWithinSchool', 'totalCountWithinSchool'])
    return(schoolDataSymbols)

def substituteSymbol(value, valueWithinSchool, mySymbols):
    """this takes a value and substitutes it with a symbol if the value is -1

    Args:
      value: integer, -1 if missing, non-negative integer otherwise
      valueWithinSchool: an integer for its position in the school dataframe
      mySymbols: list of SymPy symbols
     
    Returns:
      newValue: value if value is not -1; symbol otherwise
      """
    if value==-1:
        newValue=mySymbols[valueWithinSchool]
    else:
        newValue=value
    return(newValue) 

def equationsByMetricFile(df, equationDict, number):
    """this adds equations to the equationDict representing that the "All" Count value is the sum of all the non-All count values within each file/Tested Grade/Subject

    Args:
      df: school df with symbols
      equationDict: a dictionary with integer keys and corresponding SymPy equations
      number: highest integer key in the equationDict
     
    Returns:
      equationDict: updated with new equations
      numbers: new highest integet key in the equationDict
      
      """

    for i in list(df['Metric File'].unique()):
        number=number+1
        totalMetric=df.loc[(df['Metric File']==i) & (df['Tested Grade/Subject']=="All")]['Count'].iloc[0]
        myEquation=df.loc[(df['Metric File']==i) & (df['Tested Grade/Subject']!="All")]['Count'].values.sum()
        equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def equationsByTotalCountbyGrade(df, equationDict, number):
    """this adds equations to the equationDict representing that the Total Count value in the Levels file is the same as the sum of the Count values 

    Args:
      df: school df with symbols
      equationDict: a dictionary with integer keys and corresponding SymPy equations
      number: highest integer key in the equationDict
     
    Returns:
      equationDict: updated with new equations
      numbers: new highest integet key in the equationDict
      
      """
    nonProficientGrades= [i for i in list(df['Grade file'].unique()) if  "Proficiency" not in i]
    for i in nonProficientGrades:
        number=number+1
        totalMetric=df.loc[df['Grade file']==i]['Total Count'].iloc[0]
        myEquation=df.loc[(df['Grade file']==i)]['Count'].values.sum()
        equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def equationsTotalCounts(df, equationDict, number):
    """this adds equations to the equationDict representing that the Total Count value in the Proficiency file for All grades is the same as the sum of all of the individual grade Proficiency numbers

    Args:
      df: school df with symbols
      equationDict: a dictionary with integer keys and corresponding SymPy equations
      number: highest integer key in the equationDict
     
    Returns:
      equationDict: updated with new equations
      numbers: new highest integet key in the equationDict
      
      """
    number=number+1
    totalMetric=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']=="All")]['Total Count'].iloc[0]
    myEquation=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']!="All")]['Total Count'].values.sum()
    equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def equationsTotalCountSubject(df, equationDict, number):
    """this adds equations to the equationDict representing that the total count coming from each non-all subject is the same for each metric value

    Args:
      df: school df with symbols
      equationDict: a dictionary with integer keys and corresponding SymPy equations
      number: highest integer key in the equationDict
     
    Returns:
      equationDict: updated with new equations
      numbers: new highest integet key in the equationDict
      
      """
    nonAlls=[i for i in df['Tested Grade/Subject'].unique() if i!='All']
    for subject in nonAlls:
        for level in list(df['Metric Value'].unique()):
            number=number+1
            totalMetric=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']==subject)]['Total Count'].iloc[0]
            myEquation=df.loc[(df['Metric Value']==level) & (df['Tested Grade/Subject']==subject)]['Total Count'].iloc[0]
            equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def equationsByProficientAndLevels(df, equationDict, number):
    """this adds equations to the equationDict representing that the overall proficiency number is the sum of level 4 and 5

    Args:
      df: school df with symbols
      equationDict: a dictionary with integer keys and corresponding SymPy equations
      number: highest integer key in the equationDict
     
    Returns:
      equationDict: updated with new equations
      numbers: new highest integet key in the equationDict
      
      """
    for i in list(df.loc[df['file']=="Proficiency"]['Tested Grade/Subject'].unique()):
        number=number+1
        totalMetric=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']==i)]['Count'].iloc[0]
        myEquation=df.loc[(df['file']!="Proficiency") & (df['Tested Grade/Subject']==i) & df['Metric Value'].isin(["Performance Level 4", "Performance Level 5"])]['Count'].values.sum()
        equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict, number)

def equationsWithinProficiency(df, equationDict, number):
    """this adds equations to the equationDict representing that within the proficiency file, the All is the sum of each grade

    Args:
      df: school df with symbols
      equationDict: a dictionary with integer keys and corresponding SymPy equations
      number: highest integer key in the equationDict
     
    Returns:
      equationDict: updated with new equations
      numbers: new highest integet key in the equationDict
      
      """
    number=number+1
    totalMetric=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']=="All")]['Count'].iloc[0]
    myEquation=df.loc[(df['file']=="Proficiency") & (df['Tested Grade/Subject']!="All")]['Count'].values.sum()
    equationDict[number]= Eq((myEquation), totalMetric)
    return(equationDict)

def replaceWithSymbolsAndGenerateEquations(df, schoolNumber):
    """this takes a df for a school, substitutes symbols for missing data, and generates a dictionary of equations representing all of the data relationships

    Args:
      df: school df with symbols
      schoolNumber: integer representing what # the school is in our list of schools
     
    Returns:
      mySymbols:
      equationDict: a dictionary with integer keys and corresponding SymPy equations
      number: new highest integer key in the equationDict
      
      """
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
    equationDict, number=equationsTotalCounts(schoolData, equationDict, number)
    equationDict, number=equationsByProficientAndLevels(schoolData, equationDict, number)
    equationDict, number=equationsTotalCountSubject(schoolData, equationDict, number)
    equationDict=equationsWithinProficiency(schoolData, equationDict, number)
    return(mySymbols, number, equationDict)

def symbolicSolveASchool(schoolData, schoolName, schoolNumber):
    """this takes a df for a school, generates equations, solves them when possible, and substitutes the answer for the missing value

    Args:
      schoolData: pandas DF of the subset of data by School Name
      schoolName: string with the school name value
      schoolNumber: integer representing what # the school is in our list of schools
     
    Returns:
     schoolData: with symbols subsituted for -1s and, when the value is solved for, that value put in
      
      """
    mySymbols, number, equationDict=replaceWithSymbolsAndGenerateEquations(schoolData, schoolNumber)
    valuesInSchoolData=list(schoolData['Count'].values)+list(schoolData['Total Count'].values)
    symbolsWeUse=[i for i in valuesInSchoolData if type(i)== sympy.core.symbol.Symbol]
    mySymbols=tuple([i for i in mySymbols if i in symbolsWeUse])
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
    

def concatDatasets(subsetProf, subsetAll, subject):
    """this takes the profiency and the levels data and the subject and returns it, with some additional columns, 
    including that will let us do indexing to make sure when we put in symbols that we're not re-using any

    Args:
      subsetProf: pandas df with proficiency data
      subsetAll: pandas df with levels data
      subject: Math or ELA
     
    Returns:
     resultInitial: the concatenated data sets with some additional columns
      
      """
    resultInitial=fillDf(pd.concat([subsetProf, subsetAll]), subject)
    resultInitial['countWithinSchool']=resultInitial.groupby(['School Name']).cumcount()+1
    maxCount=resultInitial['countWithinSchool'].max()
    resultInitial['totalCountWithinSchool']=resultInitial.groupby(['School Name']).cumcount()+maxCount    
    resultInitial['Metric File']=resultInitial['Metric Value']+resultInitial['file']
    resultInitial['Grade file']=resultInitial['Tested Grade/Subject']+resultInitial['file']
    return(resultInitial)

def genData(subject):
    """this generates the initial raw data for a subject and pickles it

    Args:
      subject: string of either Math or ELA
      
    Returns:
      resultInitial:  the concatenated data sets with some additional columns.
      also, pickles this file
      
      """
    schoolFile='[5] 2021-22 School Level PARCC and MSAA Data.xlsx'
    schoolProficientTab="Proficiency"
    schoolLevelTab="Performance Level"
    subsetAll=filterDropCols(schoolFile, schoolLevelTab, "Levels")
    subsetProf=filterDropCols(schoolFile, schoolProficientTab, "Proficiency")
    subsetProf['Metric Value']="4 and 5"
    resultInitial=concatDatasets(subsetProf, subsetAll, subject)
    resultInitial.to_pickle(f'{subject}_initial.pkl') # this does some initial data cleaning -- just filling in some total counts and replacing unknows with 1
    return(resultInitial)


def iterateThroughSchoolsSymbolsSolve(resultInitial):
    """this takes the concatenated file for a subject and iterates through each school to solve with SymPy

    Args:
      subject: string of either Math or ELA
      
    Returns:
      symbolSolvedSet: this is the pandas df of schools after we've done sympy solving
      brokenSchools: a list of any schools where something 'broke' in solving
      
      """
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

def determineNumberMissingSymbols(symbolSolvedSet):
    """the concept here is that getting the count of symbols (that is, still missing variables) for each school
    this does not count unique symbols - that is, if a22 is the answer to multiple of your counts, it will count multiple times
    the thinking here is that we're using this to determine what schools to try to brute force solutions to, and each additional unsolved value
    adds another equation we have to solve for each possible set of numbers we're trying
    
    Args:
      symbolSolvedSet: pandas df with symbols in it after we've used sympy to solve what it can
      
    Returns:
      dfmissing: pandas df with School Name and Count of Missing Symbols columns
      
      """
    missingCounts=[]
    for schoolName in symbolSolvedSet['School Name'].unique():
        schoolData=symbolSolvedSet.loc[symbolSolvedSet['School Name']==schoolName]
        possibleValues=[i for i in schoolData['Count'].values if type(i)!=int] + [i for i in schoolData['Total Count'].values if type(i)!=int]
        missingCounts.append([schoolName, len(possibleValues)])
    dfmissing=pd.DataFrame(missingCounts)
    dfmissing.columns=['School Name', 'Count of Missing Symbols']
    return(dfmissing)

def testCombos(possibleValues, allCombos, unsolvedValues, myVars):
    """here we're taking a list of lists of all possible combos 
    (that is, groups of values representing the values we're trying to solve)
     and we're iterating through each set and if it 'works' (all values are >=0),
     we append and return it
    
    Args:
      possibleValues: list of list of values that work
      allCombos: list of list of constants we're testing
      unsolvedValues: unsolvedValues: these are symbols or equations that need to be >=0
      myVars: the symbols we're solving for
      
    Returns:
      possibleValues: updated list of list of values that work
      
      """
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
    """this takes a list of values and extracts all of the unique symbols from it
   
    Args:
      unsolvedValues: list of values including symbols, equations, constants
      
    Returns:
      justPositives: unique unsolved symbols
      
      """
    firstPass=[i for i in unsolvedValues if type(i)==sympy.core.symbol.Symbol]
    unflatlist=[list(i._args) for i in unsolvedValues]
    secondPass=list(set([item for sublist in unflatlist for item in sublist if type(item)==sympy.core.mul.Mul or type(item)==sympy.core.symbol.Symbol]))
    firstAndSecond=firstPass+secondPass
    plusNegatives=firstAndSecond + [i * -1 for i in firstAndSecond]
    justPositives=list(set([i for i in plusNegatives if str(i)[0]!="-"]))
    return(justPositives)

def solveIfNMissing(symbolSolvedSet, schoolName):
    """this takes a df that's been solved by SymPy and tries to brute force remaining solutions
   
    Args:
      symbolSolvedSet: pandas df
      schoolName: school name
      
    Returns:
      myVars: list of unsolved SymPy symbols
      possibleValues:  this us a list of tuples showing values that meet our constraints - that is, they could be the solutions to the symbols
      
      """
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
        print(f"possible issue {schoolName}")
    return(myVars, possibleValues) 

def getSolvesOnes(symbolSolvedSet, dfmissing,  maxSymbolsForIteration):
    """this takes schools where there are still missing variables and iterates through their data and tries to solve the remaining symbols
    the mechanism is that we know every value needs to be >=0; so this sometimes solves the equation
    sympy is not good at using that inforamtion
    Args:
      symbolSolvedSet: pandas df
      dfmissing: pandas df with School Name and Count of Missing Symbols columns
      maxSymbolsForIteration: this is the maximum amount of missingness (# of missing values) that we want to try to solve; 
      the bigger this is, the longer it will take to run but we might solve more
      
    Returns:
      dictOfReplacements: dictionary where the keys are SymPy symbols and the solutions are the value - for symbols where we found just one solution
      
      """
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
    """this takes a value and if it's not an integer, tries to substitute a dictionary of symbol/value pairs into it
    Args:
      value: this could be an integer, SymPy symbol, SymPy equation
      dictOfReplacements: dictionary where the keys are SymPy symbols and the solutions are the value - for symbols where we found just one solution
      
    Returns:
      value: this is the initial value or the initial value, with a substition made for one or more symbols
      
      """
    if type(value)!=int:
        try:
            item=value.subs(dictOfReplacements)
            return(int(item))
        except:
            return(value)
    else:
        return(value)


def genOneSubject(subject, maxSymbolsForIteration=10):
    """this runs all the data loading cleaning functions for ELA or math
    
    Args:
      subject: string for ELA or Math
      maxSymbolsForIteration: this is the maximum number of missing values a school can have where we'll try to solve for it our brute force attempts
    
    Returns:
      symbolSolvedSet: pandas df after solving, still has SymPy symbols for missing values
      """
    # generates data
    initialDataSet=genData(subject)
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
    symbolSolvedSet['OverallSubject']=subject
    return(symbolSolvedSet)
  

def runSaveBothSubjects():
    """this runs all the data loading cleaning functions for both subjects
    
    Returns:
      initialData: initial data set (with -1s for missings)
      cleanedData: final data set after all the solving
          
      """
    cleanedData=pd.concat([genOneSubject(subject="Math"), genOneSubject(subject="ELA")])
    initialData=pd.concat([pd.read_pickle("ELA_initial.pkl"), pd.read_pickle("Math_initial.pkl")])
    return(initialData, cleanedData)

   
def genMetricsBySchool(df):
    """this generates a count of total rows and count of missing values for the Count variable
    
    Args:
        df: pandas df with either -1s or non-integer values representing missing data
        
    Returns:
        metricDF: pandas df with School Name, count of total values, and count of missing values
          
      """
    metricsBySchool=[]
    for schoolName in df['School Name'].unique():
        schoolData=df.loc[df['School Name']==schoolName]
        count=len(schoolData)
        missingCount=count-len([i for i in schoolData['Count'].values if isinstance(i, numbers.Number) and i!=-1])
        metricsBySchool.append([schoolName, count, missingCount])
    metricDF=pd.DataFrame(metricsBySchool, columns=['School Name', 'Line Count', 'Missing Count'])
    return(metricDF)

def genBeforeAfterMetrics(initialData, cleanedData):
    """this generates and writes out a count of before- and after- missingness for the Count variable for 
    the levels and proficiency data (just the rows selected in filterDict() function)
    
    Args:
        initialData: initial data set (with -1s for missings)
        cleanedData: final data set after all the solving
        
    Returns:
        allMetrics: pandas df with School Name, count of total values,
        and count of missing values before and after
          
      """
    initialMissingness=genMetricsBySchool(initialData).rename(columns={"Missing Count": "Missing Count Initial"})
    finalMissingness=genMetricsBySchool(cleanedData).rename(columns={"Missing Count": "Missing Count Final"})
    beforeAndAfter=initialMissingness.merge(finalMissingness, left_on=['School Name', 'Line Count'], right_on=['School Name','Line Count'], how='outer')
    return(beforeAndAfter)
    

def main():    
    #this runs all the code -- reads the data, cleans it, outputs a csv file summarizing how many Count values were solve
    os.chdir(os.getcwd().replace("reIdentifyingPARCCData", "data"))
    initialData, cleanedData=runSaveBothSubjects()
    os.chdir(os.getcwd().replace("data", "reIdentifyingPARCCData"))
    summaryResults=genBeforeAfterMetrics(initialData, cleanedData)
    summaryResults.to_csv("Missing Count by School, Before and After.csv")


main()

