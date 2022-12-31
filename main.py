# -*- coding: utf-8 -*-
"""

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
from fractions import Fraction
"""
INPUTS: 
    
"schoolevel1.csv"
"schoolevel2.csv"

 '[5] 2021-22 School Level PARCC and MSAA Data edited.xlsx'
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
    df=df.loc[df['Subject']!="ELA"]
    missingValues=genMissingValues()
    for value in missingValues:
        df[['Total Count', 'Count']]=df[['Total Count', 'Count']].replace(value, np.NaN)
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
                    print(schoolName)
            except:
                pass
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].ffill()
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].bfill()
    df=df.fillna(-1)
    df['Total Count']= pd.to_numeric(df['Total Count'], errors='coerce')
    df['Count'] = pd.to_numeric(df['Count'], errors='coerce')
    return(df[['Tested Grade/Subject', 'Metric Value', 'Count', 'Total Count', 'file', 'Percent','School Name']])


def solveFractionWithDenominator(count, percent, total_count):
    # this takes fractions and looks at the total count
    # this is only going to work if there isn't a weird rounding thing happening
    # we could make it more flexible if we needed to
    if type(count)!=int and  percent!=-1:
        try:
            target=float(percent)/100
            denominator=total_count
            lowest_possible=Fraction(int(round(target*denominator)), denominator)
            if lowest_possible.denominator==denominator:
                return( lowest_possible.numerator)
            elif denominator % lowest_possible.denominator==0:
                return(denominator/lowest_possible.denominator * lowest_possible.numerator)   
            else: 
                print("something weird happened with fraction rounding!")
                return(-1)
        except:
            return(-1)
    else:
        return(-1)
    
def solveFractionWithDenominatorGetVar(count, percent, total_count):
    # this is only going to work if the resulting equation has only one variable
    # this takes fractions and looks at the total count
    # this is only going to work if there isn't a weird rounding thing happening
    # we could make it more flexible if we needed to
    if count==-1 and  percent!=-1:
        try:
            target=float(percent)/100
            denominator=total_count
            lowest_possible=Fraction(int(round(target*denominator)), denominator)
            #print([count, percent, total_count])
            if lowest_possible.denominator==denominator:
                newCount=( lowest_possible.numerator)
            elif denominator % lowest_possible.denominator==0:
                newCount=(denominator/lowest_possible.denominator * lowest_possible.numerator)  
            else: 
                print("something weird happened with fraction rounding!")
            #print(newCount)
            #equation=count-newCount
            #print(equation)
            #print()
            return(int(newCount))
        except:
            return(int(count))
    else:
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
    AandB=[i for i in keywords if i[0]=="a" or i[0]=="b" or i[0]=="c" or i[0]=="d"]
    myString=",".join(AandB)
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

#allForSchool
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

def iterateThroughSchoolsSymbolsSolve(levelsAndProf):
    brokenSchools=[]
    fullListDF=[]
    schoolNumber=0
    schoolNames=list(levelsAndProf['School Name'].unique())
    for schoolName in schoolNames:  
        schoolData=levelsAndProf.loc[levelsAndProf['School Name']==schoolName]
        try:
            schoolData=symbolicSolveASchool(schoolData, schoolName, schoolNumber) 
        except:
            brokenSchools.append(schoolName)
        fullListDF.append(schoolData)
        schoolNumber=schoolNumber+1
    fullDF=pd.concat(fullListDF)
    return(fullDF, brokenSchools)

def genMetricsBySchool(levelsAndProf):
    metricsBySchool=[]
    for schoolName in levelsAndProf['School Name'].unique():
        schoolData=levelsAndProf.loc[levelsAndProf['School Name']==schoolName]
        count=len(schoolData)
        missingCount=count-len([i for i in schoolData['Count'].values if type(i)==int or i==-1])
        metricsBySchool.append([schoolName, count, missingCount])
    metricDF=pd.DataFrame(metricsBySchool, columns=['School', 'Line Count', 'Missing Count'])
    return(metricDF)

def determineNumberMissingSymbols(fullDF):
    missingCounts=[]
    for schoolName in fullDF['School Name'].unique():
    # this does not work FYI but also we don't really need it
        sample=fullDF.loc[fullDF['School Name']==schoolName]
        possibleValues=set([i for i in sample['Count'].values if type(i)!=int] + [i for i in sample['Total Count'].values if type(i)!=int])
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

def solveIfNMissing(fullDF, schoolName):
    print(schoolName)
    possibleValues=[]
    sample=fullDF.loc[fullDF['School Name']==schoolName]
    unsolvedValues=list(set([i for i in sample['Count'].values if type(i)!=int] + [i for i in sample['Total Count'].values if type(i)!=int] ))
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

def getSolvesOnes(fullDF, dfmissing):
    #this takes schools where there are still missing variables and iterates through their data and tries to solve the remaining symbols
    # the mechanism is that we know every value needs to be >=0; so this sometimes solves the equation
    # sympy is not good at using that inforamtion
    selectedSchools=dfmissing.loc[(dfmissing['Count of Missing Symbols']<6) & (dfmissing['Count of Missing Symbols']>0)]['School Name']
    dictOfReplacements={}
    listOfPossible=[]
    for schoolName in selectedSchools:
        myVars, possibleValues=solveIfNMissing(fullDF, schoolName)
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

def applydict(nonintvalue, dictOfReplacements):
    # this takes a value and if it's not an integer, tries to substitute a dictionary of symbol/value pairs into it
    if type(nonintvalue)!=int:
        try:
            item=nonintvalue.subs(dictOfReplacements)
            return(int(item))
        except:
            return(nonintvalue)
    else:
        return(nonintvalue)
    


os.chdir(r"C:\Users\aehaddad\Documents")
levelsAndProf=getOrGenData(gen=True)
testInitialComplete(levelsAndProf)
initialCount=genMetricsBySchool(levelsAndProf)
levelsAndProf['Count']=levelsAndProf.apply(lambda x: solveFractionWithDenominatorGetVar(x['Count'], x['Percent'], x['Total Count']), axis=1)


print('post fraction trick')
afterFractionCount=genMetricsBySchool(levelsAndProf)


fullDF, brokenSchools=iterateThroughSchoolsSymbolsSolve(levelsAndProf)
figureOutSums(fullDF)

print(initialCount['Missing Count'].sum())
print(afterFractionCount['Missing Count'].sum())
finalCount=genMetricsBySchool(fullDF)
print(finalCount['Missing Count'].sum())


dfmissing=determineNumberMissingSymbols(fullDF)

dictOfReplacements=getSolvesOnes(fullDF, dfmissing)


# of new ones we filled in 

fullDF['Test Count']=fullDF.apply(lambda x: applydict(x['Count'], dictOfReplacements), axis=1)     
byGrade=fullDF.loc[(fullDF['file']=="All") & (fullDF['Tested Grade/Subject']!="All")]
print(sum([i for i in list(byGrade['Test Count']) if type(i)==int])-sum([i for i in list(byGrade['Count']) if type(i)==int]))
fullDF['Count']=fullDF['Test Count']

# can we get anything from percentages?

dfmissing=determineNumberMissingSymbols(fullDF)



# non-missing percents
nonMissingPercent=fullDF.loc[fullDF['Percent']!=-1]

nonMissingPercentMissingValue=determineNumberMissingSymbols(nonMissingPercent) # not accurate!!!

valuesToLookAt=[i for i in nonMissingPercent['Count'].values if type(i)!=int]
rowswithpercent=nonMissingPercent.loc[nonMissingPercent['Count'].isin(valuesToLookAt)]
# this unfortunately has some <5%s 
rowswithpercent=rowswithpercent.loc[~rowswithpercent['Percent'].str.contains("<")]
schoolExample=rowswithpercent.iloc[0]['School Name']

subsetDF=fullDF.loc[fullDF['School Name']==schoolExample]


        
           
    


# so we can see the answer to this is 3/21 -- we have a total count! 

fullDF.loc[fullDF['Percent']=="<=10%"][['Count','Total Count']]

# what we learn from this is that <=10% sometimes includes <5%
# this still looks plausibly a thing

fullDF.loc[fullDF['Percent'].str.contains("<5")][['Count', 'Total Count', 'Percent']]
listOfNonIntValues=[i for i in fullDF['Count'].values if type(i)!=int]
fullDF.loc[(fullDF['Percent'].str.contains("%")) & (fullDF['Count'].isin(listOfNonIntValues))]['School Name'].unique()
# there's really not much here with the <percentages
# in part because we're only seeing them in schools that are super missing
# for comparing with state totals

solvedByGrade=fullDF.loc[(fullDF['Metric Value']=="4 and 5") &  (~fullDF['Count'].isin(listOfNonIntValues))]
solvedByGrade['Count']=solvedByGrade['Count'].astype(float)
totalsProf=solvedByGrade.groupby('Tested Grade/Subject').sum()['Count']

tellWhatThingsTwo=subsetAll.merge(fullDF, left_on=joinCols, right_on=joinCols, how="inner")

for value in ["DS", "n<10", "<=10%"]:
    subset=tellWhatThingsTwo.loc[tellWhatThingsTwo['Count missing']==value]
    print(value)
    items=subset['Count'].unique()
    #print([i for i in items if type(i)==int])
    print(len([i for i in items if type(i)!=int]))
    # n<10 does actually seem to be n<10
    
    


