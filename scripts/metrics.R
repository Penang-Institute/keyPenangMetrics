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
  `CPI inflation, year-on-year` = req_cpi, 
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


new_dir <- "output/"
if(!dir.exists(file.path(new_dir))) dir.create(file.path(new_dir))

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
      "population" ~ scales::label_comma(suffix = "mil", accuracy = .01)(value / 1000), 
      "income_median" ~ scales::label_comma(prefix = "RM", accuracy = 1)(value), 
      .default = scales::label_number(suffix = "%", accuracy = .01)(value)
    ), 
    dataset = ifelse(name == "population", "Population", dataset)
  ) |> 
  select(dataset, value, date_format) -> ds

ds |> write.table("output/metrics.tsv", sep = "\t", row.names = FALSE, quote = FALSE)
  
path <- c(
  `Population` = "dashboards/pop.html", 
  `GDP growth` = 'dashboards/gdp.html', 
  `Median gross household income` = 'dashboards/hhinc.html', 
  `CPI inflation, year-on-year` = 'dashboards/cpi.html', 
  `Unemployment rate` = 'dashboards/labour.html'
)
ds |> 
  rename(description = dataset, subtitle = value, title = date_format) |> 
  mutate(path = path[description]) |> 
  yaml::write_yaml("output/metrics_grid.yaml", column.major = FALSE)

# update Penang Monthly Statistics RSS

library(xml2)

tmp <- tempfile()
download.file("https://www.penangmonthly.com/tag/statistics/rss", tmp)

content <- readLines(tmp)
unlink(tmp)
read_xml(content) |> 
  xml_find_all("./channel/item") |> 
  as_list() -> res

title <- sapply(res, \(x) x$title[[1]])
# date <- sapply(res, \(x) x$pubDate[[1]]) |> 
#     substr(start = 1, stop = 16) |>
#     as.Date(format = "%a, %d %b %Y")

date <- sapply(res, \(x) x[names(x) == "category"] |> 
                 unlist() |> 
                 grep(pattern = "[[:alpha:]]+\\s[[:digit:]]+", 
                      value = TRUE) |> unname()) 
date <- paste("1", date) |> as.Date(format = "%d %B %Y")


path <- sapply(res, \(x) x$link[[1]])
image <- sapply(res, \(x) attributes(x$content)$url)
author <- sapply(res, \(x) x$creator[[1]])

data.frame(
  title = title, 
  date = format(date, "%Y-%m-01"), 
  path = path, image = image, author = author
) |> yaml::write_yaml("output/penang-monthly-stats.yaml", column.major = FALSE)
