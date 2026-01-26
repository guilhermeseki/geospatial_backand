<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc" 
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  
  <NamedLayer>
    <Name>precipitation</Name>
    <UserStyle>
      <Title>Precipitation mm/24h</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap type="intervals">
              <ColorMapEntry color="#FFFFFF" quantity="0" opacity="0"/>
              <ColorMapEntry color="#E0FFFF" quantity="4" opacity="1"/>
              <ColorMapEntry color="#ADD8E6" quantity="6" opacity="1"/>
              <ColorMapEntry color="#87CEEB" quantity="8" opacity="1"/>
              <ColorMapEntry color="#0000FF" quantity="10" opacity="1"/>
              <ColorMapEntry color="#00CED1" quantity="15" opacity="1"/>
              <ColorMapEntry color="#00FF00" quantity="20" opacity="1"/>
              <ColorMapEntry color="#ADFF2F" quantity="30" opacity="1"/>
              <ColorMapEntry color="#FFFF00" quantity="40" opacity="1"/>
              <ColorMapEntry color="#FFD700" quantity="50" opacity="1"/>
              <ColorMapEntry color="#FF8C00" quantity="75" opacity="1"/>
              <ColorMapEntry color="#FF0000" quantity="100" opacity="1"/>
              <ColorMapEntry color="#DC143C" quantity="125" opacity="1"/>
              <ColorMapEntry color="#FF69B4" quantity="150" opacity="1"/>
              <ColorMapEntry color="#9932CC" quantity="175" opacity="1"/>
              <ColorMapEntry color="#800080" quantity="200" opacity="1"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>