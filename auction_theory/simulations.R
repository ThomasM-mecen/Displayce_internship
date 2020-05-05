verif_uniform = function(n, nombre_occurence){
  cible = round(n/(n+1),2)
  max_unif = NULL
  for (i in 1:nombre_occurence){
    max_unif = c(max_unif, max(runif(n, min = 0, max = 1)))
  }
  result = round(mean(max_unif),2)
  return(paste("The average maximal draw is",result,"and theoretically it should be",cible,sep=" "))
}
verif_uniform(100,10000)
