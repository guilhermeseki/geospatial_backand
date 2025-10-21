<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld" xmlns="http://www.opengis.net/sld" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>Default Styler</sld:Name>
    <sld:UserStyle>
      <sld:Name>Default Styler</sld:Name>
      <sld:Title>Temperature Style (Celsius)</sld:Title>
      <sld:Abstract>Color ramp from cold (blue) to hot (red) for temperature data in Celsius</sld:Abstract>
      <sld:FeatureTypeStyle>
        <sld:Name>name</sld:Name>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ColorMap>
              <sld:ColorMapEntry color="#08006B" opacity="1" quantity="-10" label="-10°C"/>
              <sld:ColorMapEntry color="#1548AD" opacity="1" quantity="0" label="0°C"/>
              <sld:ColorMapEntry color="#4393C3" opacity="1" quantity="5" label="5°C"/>
              <sld:ColorMapEntry color="#7FB8D4" opacity="1" quantity="10" label="10°C"/>
              <sld:ColorMapEntry color="#ABD9E9" opacity="1" quantity="15" label="15°C"/>
              <sld:ColorMapEntry color="#D1EEF7" opacity="1" quantity="20" label="20°C"/>
              <sld:ColorMapEntry color="#FFFFBF" opacity="1" quantity="25" label="25°C"/>
              <sld:ColorMapEntry color="#FEE090" opacity="1" quantity="30" label="30°C"/>
              <sld:ColorMapEntry color="#FDAE61" opacity="1" quantity="35" label="35°C"/>
              <sld:ColorMapEntry color="#F46D43" opacity="1" quantity="40" label="40°C"/>
              <sld:ColorMapEntry color="#D73027" opacity="1" quantity="45" label="45°C"/>
              <sld:ColorMapEntry color="#A50026" opacity="1" quantity="50" label="50°C"/>
              <sld:ColorMapEntry color="#8B0000" opacity="1" quantity="55" label="55°C"/>
              <sld:ColorMapEntry color="#67001F" opacity="1" quantity="60" label="60°C"/>
            </sld:ColorMap>
            <sld:ContrastEnhancement/>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>