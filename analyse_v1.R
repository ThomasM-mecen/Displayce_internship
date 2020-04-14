library(tidyverse)
library(data.table)
library(jsonlite)
library(ndjson)
library(janitor)
options(scipen=999) 
data=ndjson::stream_in("sample_br_pop.json")
data = data %>% clean_names()
data = mutate_all(data, list(~na_if(.,"")))
data = data %>%
  remove_empty(c("rows", "cols"))
data = data %>% mutate_each(list(~./1000), starts_with('source_timestamp')) %>% 
  mutate_each(list(~as.POSIXct(.,origin="1970-01-01",tz="America/Toronto")),
                                    starts_with('source_timestamp'))
data %>% select(starts_with("source_timestamp"))

##---------------------------------------------------------------------------------------------
data=ndjson::stream_in("sample_br.json")
databis = data %>% clean_names()
databis = mutate_all(databis, list(~na_if(.,"")))
databis = databis %>%
  remove_empty(c("rows", "cols"))