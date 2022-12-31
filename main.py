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
from fractions import Fraction
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
            except:
                pass
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].ffill()
    df['Total Count']=df.groupby(['School Name', 'Tested Grade/Subject'])['Total Count'].bfill()
    df=df.fillna(-1)
    df['Total Count']= pd.to_numeric(df['Total Count'], errors='coerce')
    df['Count'] = pd.to_numeric(df['Count'], errors='coerce')
    return(df[['Tested Grade/Subject', 'Metric Value', 'Count', 'Total Count', 'file', 'Percent','School Name']])

def replaceWithSymbols(schoolData, mySymbols):    
    schoolData['Count']=schoolData.apply(lambda x: substituteSymbol(x['Count'], x['countWithinSchool'], mySymbols), axis=1)
    schoolData['Total Count']=schoolData.apply(lambda x: substituteSymbol(x['Total Count'], x['totalCountWithinSchool'], mySymbols), axis=1)
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
    AandB=[i for i in keywords if i[0]=="a" or i[0]=="b" or i[0]=="c" or i[0]=="d"]
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

def iterateThroughSchoolsSolve(levelsAndProf):
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
    
    # we need to scope this
    """
    there are a couple potential ways of doing this
    one would be to do so based on the property that the area of possible values is continuous
    so if there's a 0 that works, and then 1 doesn't, then 2 won't
    
    another is to do so based on the values of the non-missing values -- if the total is 20, and we already have a 9 and an 8, then
    each remaining value has got to be under 4.
    
    I think we can do the budget version of #1, where we start with 0-5, and if either no values are found or if one value is a 5 ,we keep going
    """
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
    selectedSchools=dfmissing.loc[(dfmissing['Count of Missing Symbols']<6) & (dfmissing['Count of Missing Symbols']>0)]['School Name']
    # this takes awhile to run
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
    if type(nonintvalue)!=int:
        try:
            item=nonintvalue.subs(dictOfReplacements)
            return(int(item))
        except:
            return(nonintvalue)
    else:
        return(nonintvalue)
    
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
    
os.chdir(r"C:\Users\aehaddad\Documents")
levelsAndProf=getOrGenData(gen=False)
testInitialComplete(levelsAndProf)
initialCount=genMetricsBySchool(levelsAndProf)



levelsAndProf['Count']=levelsAndProf.apply(lambda x: solveFractionWithDenominatorGetVar(x['Count'], x['Percent'], x['Total Count']), axis=1)

print('post fraction trick')
afterFractionCount=genMetricsBySchool(levelsAndProf)




fullDF, brokenSchools=iterateThroughSchoolsSolve(levelsAndProf)
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


# do we have count/percent pairs where percent is non-missing (not -1) but where there is a non-int value for the Count

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
"""
# let's look at what's going on at schools with Algebra

algebraSchools=fullDF.loc[fullDF['Tested Grade/Subject']=="Algebra I"]['School Name'].unique()

# Browne Education Campus - should have figured out that everything that's not solved for math for count for proficiency is 0
# Eliot-Hine Middle School is an example of having the overall proficiency count but not algebra
# there are other schools like Browne -- see Johnson Middle School, Kramer Middle School
# maybe we didn't try because they have too many variables
# also we're understating the effect of this process because it's solving almost more variables than people
# yes! 5-6, 9
# this is working now but it takes a long time to run because we're not very efficienctly searching the sample space
# I think to make expanding this possible we need to scope this based on the possible size based on the school

for school in algebraSchools[0:10]:
    print(school)
    sample=fullDF.loc[fullDF['School Name']==schoolName]
    subsample=sample.loc[sample['file']=="Proficiency"]
    print(subsample[['Tested Grade/Subject', 'Count']])
    print()
    # omg this is so much better now so why are we still seeing this issue
[i for i in fullDF.loc[(fullDF["Tested Grade/Subject"]=="Algebra I") & (fullDF["file"]=="Proficiency")]['Count'] if type(i)!=int]
# ok we are still seeing some unsolved ones

listOfUnsolved= [i for i in fullDF.loc[(fullDF["Tested Grade/Subject"]=="Algebra I") & (fullDF["file"]=="Proficiency")]['Count'] if type(i)!=int]
fullDF.loc[fullDF['Count'].isin(listOfUnsolved)][['School Name', 'Count']]
# so we do see a bunch of schools
   

"""
algebraValues=fullDF.loc[(fullDF["Tested Grade/Subject"]=="Algebra I") & (fullDF["file"]=="Proficiency")]
# do we have any solutions where we solved one variable but not another?
# we're interested in whether the original 'values' say anything about the actual value

# we're going to get this by reading in the original and merging it
"""
schoolFile='[5] 2021-22 School Level PARCC and MSAA Data edited.xlsx'
schoolProficientTab="Proficiency"
schoolProficientData=genCleanSchool(schoolFile, schoolProficientTab)
schoolProficientData['file']="Proficiency"
joinCols=['Tested Grade/Subject',
 'file',
 'School Name']
schoolProficientData=schoolProficientData.rename(columns={"Count": "Count missing", "Total Count": "Total count missing"}).drop(columns=["Percent"])
schoolProficientData=schoolProficientData.loc[schoolProficientData['Subject']!="ELA"]

tellWhatThings=schoolProficientData.merge(fullDF, left_on=joinCols, right_on=joinCols, how="inner")

for value in ["DS", "n<10", "<=10%"]:
    subset=tellWhatThings.loc[tellWhatThings['Count missing']==value]
    print(value)
    items=subset['Count'].unique()
    print([i for i in items if type(i)==int])
    # n<10 does actually seem to be n<10
    
schoolLevelTab="Performance Level"
subsetAll=cleanSchoolLevels(schoolFile, schoolLevelTab)

subsetAll['file']="All"
joinCols=['Tested Grade/Subject',
 'file',
 'School Name']
subsetAll=subsetAll.rename(columns={"Count": "Count missing", "Total Count": "Total count missing"}).drop(columns=["Percent"])
subsetAll=subsetAll.loc[subsetAll['Subject']!="ELA"]

tellWhatThingsTwo=subsetAll.merge(fullDF, left_on=joinCols, right_on=joinCols, how="inner")

for value in ["DS", "n<10", "<=10%"]:
    subset=tellWhatThingsTwo.loc[tellWhatThingsTwo['Count missing']==value]
    print(value)
    items=subset['Count'].unique()
    #print([i for i in items if type(i)==int])
    print(len([i for i in items if type(i)!=int]))
    # n<10 does actually seem to be n<10
    
    

fullDF


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