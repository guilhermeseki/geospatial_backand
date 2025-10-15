#check dimensions avaliable
curl "http://localhost:8080/geoserver/wms?service=WMS&version=1.3.0&request=GetCapabilities&layers=precipitation_ws:chirps" | grep "Dimension name"
