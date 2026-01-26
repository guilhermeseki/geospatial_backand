<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>precipitation_style</Name>
    <UserStyle>
      <Title>Precipitation Style</Title>
      <Abstract>Precipitation colormap ranging from light blue (low) through green/yellow to purple (very high)</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap type="ramp">
              <ColorMapEntry color="#FFFFFF" quantity="0"   label="0 mm" opacity="0"/>
              <ColorMapEntry color="#E0FFFF" quantity="1"   label="1 mm" opacity="1"/>
              <ColorMapEntry color="#ADD8E6" quantity="5"   label="5 mm" />
              <ColorMapEntry color="#87CEEB" quantity="10"  label="10 mm" />
              <ColorMapEntry color="#00CED1" quantity="15"  label="15 mm" />
              <ColorMapEntry color="#00FF00" quantity="20"  label="20 mm" />
              <ColorMapEntry color="#ADFF2F" quantity="30"  label="30 mm" />
              <ColorMapEntry color="#FFFF00" quantity="40"  label="40 mm" />
              <ColorMapEntry color="#FFD700" quantity="50"  label="50 mm" />
              <ColorMapEntry color="#FF8C00" quantity="75"  label="75 mm" />
              <ColorMapEntry color="#FF0000" quantity="100" label="100 mm" />
              <ColorMapEntry color="#DC143C" quantity="125" label="125 mm" />
              <ColorMapEntry color="#FF69B4" quantity="150" label="150 mm" />
              <ColorMapEntry color="#9932CC" quantity="175" label="175 mm" />
              <ColorMapEntry color="#800080" quantity="200" label="200 mm" />
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
