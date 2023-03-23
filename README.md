# reIdentifyingPARCCData

For more about this project, see: https://blog.capitaltg.com/inferring-hidden-data-by-solving-linear-equations-in-python/

**The data set this runs on is no longer publicly available; this is offered for illustrative purposes.**

This un-redacts some of the missing data in the '[5] 2021-22 School Level PARCC and MSAA Data.xlsx' focusing on grade- and school-level PARCC data for both Profiency and Levels. 

### The strategies here are:

  #1. Fill in missing 'Total Count' data at the grade- and school-level using non-missing data, because Total Count is the same within grade but across levels/proficiency.
  
  #2. Use the combination of the 'Total Count' and the Percent data to generate 'Count', since Count/Total Count = Percent
  
  #3. Use Sympy and the relationships between the data (for instance, each school is the sum of all of its grades, and the proficiency counts are the sum of levels 4 and 5) to set up and solve equations.
  
  #4. Iterate through remaining missing values to see if there's only one possible solution for remaining variables. (This is sometimes the case because Sympy is not good at using the fact that every variable here must be a non-negative integer, so sometimes just setting up all unsolved equations as >=0 and iterating through all possible options finds an answer.)
  
### The two things that add a lot of time to run are:

  #1. Generating a lot of SymPy symbols
  
  #2. Generating and testing all the possible options in #4 to try to solve equations/variables we're not able to solve via Sympy (basically, iterating through all possible choices)
    
The first issue, we control in the function replaceWithSymbolsAndGenerateEquations.

The line that controls the number of variables creates is:

AthroughD=[i for i in keywords if i[0]=="a" or i[0]=="b" or i[0]=="c" or i[0]=="d"]

If you needed more variables, you'd go later in the alphabet. (for instance, if we wanted to add in functionality for looking at all the subgroup missing data, which this code currently drops)
    
The second issue, we control via the maxSymbolsForIteration parameter. If you set that higher, it will attempt to solve (and in some cases, solve) unsolved count variables for schools with more data that's still unsolved after trying to solve it mathematically via
SymPy-- but because it's iterating through every possible option, if you set this higher, it will take a really long time to run -- much longer than everything else combined.

### Inputs:

File: '[5] 2021-22 School Level PARCC and MSAA Data.xlsx'
Tabs: "Proficiency", "Performance Level"

### Outputs:

ELA_initial.pkl and Math_initial_pkl - files with some light cleaning done (substution of -1s for missing values)

Missing Count by School, Before and After.csv : this summarizes the number of Count values that were missing at the beginning and at the end. (We're only looking for values for PARCC at the grade- and school-level for both proficiency and levels)
