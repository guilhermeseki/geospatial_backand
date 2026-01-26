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
      <Title>Lightning Activity Classification</Title>
      <Abstract>
        GLM FED classification with progressive intensity scale:
        0: Sem descargas
        1-5: Muito fraca a fraca (dark purple to purple)
        8-12: Fraca a moderada (purple to darker purple)
        20-35: Moderada a forte (purple to dark blue)
        50-75: Moderada a forte (blue shades)
        100-150: Forte a muito forte (cyan shades)
        200-300: Muito forte a tempestade forte (cyan to green)
        400-600: Tempestade intensa a muito intensa (green to yellow)
        800-1100: Tempestade severa a severidade elevada (yellow to orange)
        1500-2000+: Extrema (red shades)
      </Abstract>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
            <ColorMap type="ramp">
              <!-- 0: Sem descargas -->
              <ColorMapEntry color="#000000" quantity="0" opacity="0.0"/>

              <!-- 1-5: Muito fraca a fraca -->
              <ColorMapEntry color="#16002b" quantity="1" opacity="0.25"/>
              <ColorMapEntry color="#24004d" quantity="3" opacity="0.35"/>
              <ColorMapEntry color="#330066" quantity="5" opacity="0.45"/>

              <!-- 8-12: Fraca a moderada fraca -->
              <ColorMapEntry color="#3f0080" quantity="8" opacity="0.55"/>
              <ColorMapEntry color="#4d0099" quantity="12" opacity="0.65"/>

              <!-- 20-35: Moderada a forte -->
              <ColorMapEntry color="#5c00b3" quantity="20" opacity="0.75"/>
              <ColorMapEntry color="#0000cc" quantity="35" opacity="0.82"/>

              <!-- 50-75: Moderada a forte -->
              <ColorMapEntry color="#0033ff" quantity="50" opacity="0.85"/>
              <ColorMapEntry color="#0066ff" quantity="75" opacity="0.88"/>

              <!-- 100-150: Forte a muito forte -->
              <ColorMapEntry color="#0099ff" quantity="100" opacity="0.90"/>
              <ColorMapEntry color="#00ccff" quantity="150" opacity="0.92"/>

              <!-- 200-300: Muito forte a tempestade forte -->
              <ColorMapEntry color="#00ffcc" quantity="200" opacity="0.94"/>
              <ColorMapEntry color="#66ff66" quantity="300" opacity="0.95"/>

              <!-- 400-600: Tempestade intensa a muito intensa -->
              <ColorMapEntry color="#ccff33" quantity="400" opacity="0.96"/>
              <ColorMapEntry color="#ffff00" quantity="600" opacity="0.97"/>

              <!-- 800-1100: Tempestade severa a severidade elevada -->
              <ColorMapEntry color="#ffcc00" quantity="800" opacity="0.98"/>
              <ColorMapEntry color="#ff9900" quantity="1100" opacity="0.99"/>

              <!-- 1500-2000+: Extrema -->
              <ColorMapEntry color="#ff3300" quantity="1500" opacity="1.0"/>
              <ColorMapEntry color="#cc0000" quantity="2000" opacity="1.0"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
