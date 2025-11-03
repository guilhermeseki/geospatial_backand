<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>GLM Flash Extent Density</Name>
    <UserStyle>
      <Title>Lightning Flash Extent Density</Title>
      <Abstract>Color ramp for GLM Flash Extent Density - Dark purple to white representing increasing lightning activity</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap type="ramp">
              <!-- No lightning: Transparent -->
              <ColorMapEntry color="#000000" quantity="0" opacity="0" label="No Lightning"/>

              <!-- Very low activity: Dark purple -->
              <ColorMapEntry color="#1a0033" quantity="1" opacity="0.3" label="Very Low"/>
              <ColorMapEntry color="#330066" quantity="5" opacity="0.5" label="Low"/>

              <!-- Low-moderate: Purple to blue -->
              <ColorMapEntry color="#4d0099" quantity="10" opacity="0.7" label="Moderate Low"/>
              <ColorMapEntry color="#6600cc" quantity="20" opacity="0.8" label="Moderate"/>

              <!-- Moderate: Blue -->
              <ColorMapEntry color="#0000ff" quantity="50" opacity="0.85" label="Moderate High"/>

              <!-- Moderate-high: Cyan -->
              <ColorMapEntry color="#00ccff" quantity="100" opacity="0.9" label="High"/>

              <!-- High: Yellow-green -->
              <ColorMapEntry color="#00ff99" quantity="200" opacity="0.95" label="Very High"/>
              <ColorMapEntry color="#ffff00" quantity="400" opacity="0.95" label="Intense"/>

              <!-- Very high: Orange -->
              <ColorMapEntry color="#ff9900" quantity="800" opacity="1.0" label="Very Intense"/>

              <!-- Extreme: Red -->
              <ColorMapEntry color="#ff0000" quantity="1500" opacity="1.0" label="Extreme"/>

              <!-- Exceptional: Bright red to white -->
              <ColorMapEntry color="#ff66ff" quantity="3000" opacity="1.0" label="Exceptional"/>
              <ColorMapEntry color="#ffffff" quantity="5000" opacity="1.0" label="Extraordinary"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
