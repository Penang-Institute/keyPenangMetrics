# Retrieve metrics from OpenDOSM API falling back on datasets where not available
library(httr2)
library(dplyr)
library(purrr)

base_request <- httr2::request("https://api.data.gov.my/data-catalogue?")

req_gdp_growth <- base_request |>
  req_url_query(
    id = "gdp_state_real_supply",
    sort = "-date",
    ifilter = "pulau pinang@state",
    filter = "p0@sector",
    contains = "growth_yoy@series",
    limit = 1,
    include = "date,value"
  )
req_perform(req_gdp_growth) |> resp_body_json()

req_income <- base_request |>
  req_url_query(
    id = "hh_income_state",
    sort = "-date",
    ifilter = "pulau pinang@state",
    include = "date,income_median",
    limit = 1
  )

req_cpi <- base_request |>
  req_url_query(
    id = "cpi_state_inflation",
    sort = "-date",
    ifilter = "pulau pinang@state",
    filter = "overall@division",
    include = "date,inflation_yoy",
    limit = 1
  )

req_perform(req_cpi) |> resp_body_json() 

req_ur <- base_request |>
  req_url_query(
    id = "lfs_qtr_state",
    sort = "-date",
    ifilter = "pulau pinang@state",
    include = "date,u_rate",
    limit = 1
  )

list(
  `GDP growth` = req_gdp_growth, 
  `Median gross household income` = req_income, 
  `Year-on-year CPI inflation` = req_cpi, 
  `Unemployment rate` = req_ur
) |> 
  purrr::map(req_perform) |> 
  purrr::map(resp_body_json) |> 
  list_flatten() |> 
  tibble::as_tibble_col() |> 
  mutate(dataset = names(value)) |> 
  tidyr::unnest_wider(value) |> 
  tidyr::pivot_longer(-c(date, dataset), values_drop_na = TRUE) |> 
  mutate(date = as.Date(date)) -> response_bodies_summarized

req_perform(req_ur) |> resp_body_json()

arrow::read_parquet(
  "https://storage.dosm.gov.my/population/population_state.parquet",
  as_data_frame = FALSE
) |>
  filter(sex == "both",
         age == 'overall',
         ethnicity == "overall",
         state == "Pulau Pinang") |>
  collect() |>
  filter(date == max(date)) |> 
  select(date, population) |> 
  tidyr::pivot_longer(-date) |> 
  bind_rows(response_bodies_summarized) |> 
  mutate(
    quarter = (lubridate::month(date) + 2) %/% 3,
    date_format = case_match(
      name,
      c("population", "value", "income_median") ~ format(date, "%Y"),
      "inflation_yoy" ~ format(date, "%b %Y"),
      "u_rate" ~ paste0("Q", quarter, " ", format(date, "%Y"))
    ), 
    value = case_match(
      name, 
      "population" ~ scales::label_comma()(value * 1000), 
      "income_median" ~ scales::label_comma(prefix = "RM", accuracy = 1)(value), 
      .default = scales::label_number(suffix = "%", accuracy = .01)(value)
    ), 
    dataset = ifelse(name == "population", "Population", dataset)
  ) |> 
  select(dataset, value, date_format) |> 
  write.table("output/metrics.tsv", sep = "\t", row.names = FALSE, quote = FALSE)
  
