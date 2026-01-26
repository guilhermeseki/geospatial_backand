<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld
  http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">

  <NamedLayer>
    <Name>glm_fed</Name>
    <UserStyle>
      <Title>Densidade de Descargas Elétricas (GLM)</Title>
      <Abstract>Densidade máxima de descargas em 30 minutos</Abstract>

      <FeatureTypeStyle>

        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>

            <ColorMap type="intervals">

              <ColorMapEntry color="#000000" opacity="0.0" quantity="0" label="0 – Sem descargas"/>

              <ColorMapEntry color="#16002b" opacity="0.25" quantity="1" label="1 – Muito fraca"/>
              <ColorMapEntry color="#24004d" opacity="0.35" quantity="3" label="3 – Fraca"/>
              <ColorMapEntry color="#330066" opacity="0.45" quantity="5" label="5 – Fraca"/>

              <ColorMapEntry color="#3f0080" opacity="0.55" quantity="8" label="8 – Fraca a moderada"/>
              <ColorMapEntry color="#4d0099" opacity="0.65" quantity="12" label="12 – Moderada fraca"/>

              <ColorMapEntry color="#5c00b3" opacity="0.75" quantity="20" label="20 – Moderada"/>
              <ColorMapEntry color="#0000cc" opacity="0.82" quantity="35" label="35 – Moderada a forte"/>

              <ColorMapEntry color="#0033ff" opacity="0.85" quantity="50" label="50 – Moderada a forte"/>
              <ColorMapEntry color="#0066ff" opacity="0.88" quantity="75" label="75 – Forte"/>

              <ColorMapEntry color="#0099ff" opacity="0.90" quantity="100" label="100 – Forte"/>
              <ColorMapEntry color="#00ccff" opacity="0.92" quantity="150" label="150 – Muito forte"/>

              <ColorMapEntry color="#00ffcc" opacity="0.94" quantity="200" label="200 – Muito forte"/>
              <ColorMapEntry color="#66ff66" opacity="0.95" quantity="300" label="300 – Tempestade forte"/>

              <ColorMapEntry color="#ccff33" opacity="0.96" quantity="400" label="400 – Tempestade intensa"/>
              <ColorMapEntry color="#ffff00" opacity="0.97" quantity="600" label="600 – Muito intensa"/>

              <ColorMapEntry color="#ffcc00" opacity="0.98" quantity="800" label="800 – Tempestade severa"/>
              <ColorMapEntry color="#ff9900" opacity="0.99" quantity="1100" label="1100 – Severidade elevada"/>

              <ColorMapEntry color="#ff3300" opacity="1.0" quantity="1500" label="1500 – Extrema"/>
              <ColorMapEntry color="#cc0000" opacity="1.0" quantity="2000" label="≥2000 – Extrema (MCS/Supercélula)"/>

            </ColorMap>
          </RasterSymbolizer>
        </Rule>

      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
