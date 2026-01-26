<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>wind_speed</Name>
    <UserStyle>
      <Title>Wind Speed - Intensity (km/h)</Title>
      <Abstract>Color ramp for wind speed from 0 km/h (calm) to 200+ km/h (extreme)</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap type="ramp">
              <ColorMapEntry color="#E6F2FF" quantity="0"   label="0 km/h" opacity="0"/>
              <ColorMapEntry color="#CCE5FF" quantity="5"   label="5 km/h"/>
              <ColorMapEntry color="#99CCFF" quantity="10"  label="10 km/h"/>
              <ColorMapEntry color="#66B3FF" quantity="15"  label="15 km/h"/>
              <ColorMapEntry color="#3399FF" quantity="20"  label="20 km/h"/>
              <ColorMapEntry color="#00BFFF" quantity="25"  label="25 km/h"/>
              <ColorMapEntry color="#00CED1" quantity="30"  label="30 km/h"/>
              <ColorMapEntry color="#00E5B8" quantity="35"  label="35 km/h"/>
              <ColorMapEntry color="#00FF9F" quantity="40"  label="40 km/h"/>
              <ColorMapEntry color="#7FFF00" quantity="45"  label="45 km/h"/>
              <ColorMapEntry color="#ADFF2F" quantity="50"  label="50 km/h"/>
              <ColorMapEntry color="#FFFF00" quantity="60"  label="60 km/h"/>
              <ColorMapEntry color="#FFD700" quantity="70"  label="70 km/h"/>
              <ColorMapEntry color="#FFAA00" quantity="80"  label="80 km/h"/>
              <ColorMapEntry color="#FF8800" quantity="90"  label="90 km/h"/>
              <ColorMapEntry color="#FF6600" quantity="100" label="100 km/h"/>
              <ColorMapEntry color="#FF4400" quantity="120" label="120 km/h"/>
              <ColorMapEntry color="#FF0000" quantity="140" label="140 km/h"/>
              <ColorMapEntry color="#CC0000" quantity="160" label="160 km/h"/>
              <ColorMapEntry color="#990000" quantity="180" label="180 km/h"/>
              <ColorMapEntry color="#660000" quantity="200" label="200 km/h"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
