while :
do
    scrapy crawl telegram -a channels_file=channels.json -a fetch_times=crawler/fetch_times.json -a hours=24
done
