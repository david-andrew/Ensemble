#used to call matlab from generate_recipe.py.
#The command line argument specifies which recipe to follow
matlab -nodisplay -nosplash -r "perform('recipes/$1')" 