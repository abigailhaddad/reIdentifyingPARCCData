import pandas as pd
import os
from fractions import Fraction
import math

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

def showFourthGradeIssue():
    """
    The steps here are:
        1. Get total count from the state data for # of ELA PARCC proficient fourth graders
        2. Get initial (with redactions) school-wide data for this group
        3. Get total counts by school for 4th grade ELA using the levels data
        4. Merge this in; show that the methodology works 
        5. Get total possible counts for proficiency by school using the count data for non-redacted schools and the percent data for redacted schools
    """
    fourthGradeELAProficiencybyState=genFourthGradeELAProficiencybyState()
    fourthGradeELAProficiencybySchool=genFourthGradeELAProficiencybySchool()
    totalCountsForFourthGradeELAbySchool=genTotalCountsForFourthGradeELAbySchool()
    mergedForTotalCounts=fourthGradeELAProficiencybySchool.merge(totalCountsForFourthGradeELAbySchool, left_on="School Name", right_on="School Name")
    # here we're saying: if the only Total Counts which are different between the Levels and Proficiency file are those which were initially redacted ("DS") in the proficiency file,
    # this confirms our methodology for imputing Total Count
    differences=list(mergedForTotalCounts.loc[mergedForTotalCounts['Total Count']!=mergedForTotalCounts['Total Count Imputation From Levels File']]['Total Count'].unique())
    if differences==["DS"]:
        print("Methodology is working for Total Count")
    else:
        print("Methdology is not working for Total Count")
    mergedForTotalCounts['Max Possible Count']=mergedForTotalCounts.apply(lambda x: genGreatestPossibleNumber(x['Count'], x['Percent'], x['Total Count Imputation From Levels File']), axis=1)
        # generates symbols via sympy and solves what can be solved symbolically
    maxSum= mergedForTotalCounts['Max Possible Count'].sum()
    
    sumDF=pd.DataFrame(data={"Total 4th grade ELA proficiency from state file": [fourthGradeELAProficiencybyState], 
                       "Max possible total from school file": [maxSum]})
    print(f'total from state file: {fourthGradeELAProficiencybyState}')
    print(f'max possible total from school file: {maxSum}')
    return(sumDF, mergedForTotalCounts)

def genGreatestPossibleNumber(count, percent, total_count):
    total_count=int(total_count)
    # if we have the count value already (it's not DS), this returns that value
    if count!="DS":
        pass
    elif percent=="<5%":
        count=math.floor(.05* total_count)
    elif percent=="<=10%":
        count=math.floor(.1* total_count)
    else:
        count=solveFractionWithDenominatorGetVar(-1, percent, total_count)
        pass
    return(int(count))

def genFourthGradeELAProficiencybySchool():
    schoolFile='[5] 2021-22 School Level PARCC and MSAA Data.xlsx'
    schoolProficientTab="Proficiency"
    df=pd.read_excel(schoolFile, schoolProficientTab)
    filterDict={"Assessment Name": "PARCC",
               "Grade of Enrollment": "All",
               "Student group": "All",
               'Tested Grade/Subject': "Grade 4",
              "Subject": "ELA"}
    for item in list(filterDict.keys()):
        df=df.loc[df[item]==filterDict[item]]
    return(df)
        
def genFourthGradeELAProficiencybyState():
    # this returns the number of 4th graders testing proficient in ELA state-wide on the PARCC
    stateFile="[3] 2021-22 State Level PARCC and MSAA Data.xlsx"
    stateProficientTab="Proficiency"
    df=pd.read_excel(stateFile, stateProficientTab)
    # we're subsetting on each variable that's the key in these key-value pairs to get just the data that = the value
    filterDict={"Assessment Name": "PARCC",
               "Student Group": "All",
               "Grade of Enrollment": "All",
               'Tested Grade/Subject': "Grade 4",
              "Subject": "ELA"} 
    for item in list(filterDict.keys()):
        df=df.loc[df[item]==filterDict[item]]
    return(int(df['Count'].iloc[0]))
    
def genTotalCountsForFourthGradeELAbySchool():
    # some of the Total Counts are missing for the school-level proficiency data;
    # so we get them from the levels data
    schoolFile='[5] 2021-22 School Level PARCC and MSAA Data.xlsx'
    schoolLevelTab="Performance Level"
    df=pd.read_excel(schoolFile, schoolLevelTab)
    filterDict={"Assessment Name": "PARCC",
               "Grade of Enrollment": "All",
               "Student group": "All",
               'Tested Grade/Subject': "Grade 4",
              "Subject": "ELA"}
    for item in list(filterDict.keys()):
        df=df.loc[df[item]==filterDict[item]]
    # we drop the missing (DS) values
    df=df.loc[df['Total Count']!="DS"]
    fourthGradeELATotalCount=df.groupby('School Name').first()[['Total Count']].reset_index()
    fourthGradeELATotalCount.columns=["School Name", "Total Count Imputation From Levels File"]
    return(fourthGradeELATotalCount)
    
#os.chdir(r"C:\Users\aehaddad\Documents")
os.chdir(r"C:\Users\abiga\OneDrive\Documents\Python Scripts\parcc\data")
sumDF, fourthGradeProficiencyELAData=showFourthGradeIssue()


writer = pd.ExcelWriter('Fourth Grade ELA Proficiency Sums.xlsx')

# Write each dataframe to a different worksheet.
sumDF.to_excel(writer, sheet_name='Totals')
fourthGradeProficiencyELAData.to_excel(writer, sheet_name='By School')
writer.close()