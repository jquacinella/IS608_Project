library(ggplot2)
map_data <- read.csv('map.csv')
map_data$id <- as.factor(map_data$id)
ggplot(map_data) +
    geom_bar(aes(x=id, y=consumption), stat="identity", fill="#3366FF") +
    ylim(0,2500000)