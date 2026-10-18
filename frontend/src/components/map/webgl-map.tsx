"use client";
import { useEffect, useRef } from "react";
import DeckGL from "@deck.gl/react";
import { ArcLayer, PolygonLayer } from "@deck.gl/layers";
import { cellToBoundary } from "h3-js";
import { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { GeoHexAnomaly } from "@/types/chakravyuh";
import type { PickingInfo } from "@deck.gl/core";
type Props = {
  reports: GeoHexAnomaly[];
  onSelect: (cell: string) => void;
  onFailure: () => void;
};
export default function WebGLMap({ reports, onSelect, onFailure }: Props) {
  const host = useRef<HTMLDivElement>(null),
    map = useRef<MapLibreMap | null>(null);
  const center = reports[0];
  const initial = {
    longitude: center?.longitude ?? 80,
    latitude: center?.latitude ?? 25,
    zoom: 3.2,
    pitch: 0,
    bearing: 0,
  };
  useEffect(() => {
    if (!host.current) return;
    try {
      map.current = new MapLibreMap({
        container: host.current,
        center: [initial.longitude, initial.latitude],
        zoom: initial.zoom,
        interactive: false,
        attributionControl: false,
        style: {
          version: 8,
          sources: {
            land: { type: "geojson", data: "/maps/land.geojson" },
          },
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": "#0b1526" },
            },
            {
              id: "land",
              type: "fill",
              source: "land",
              paint: {
                "fill-color": "#16273b",
                "fill-outline-color": "#385069",
              },
            },
          ],
        },
      });
      map.current.on("error", onFailure);
    } catch {
      onFailure();
    }
    return () => {
      map.current?.remove();
      map.current = null;
    };
    // Initial view is intentionally stable while the selected snapshot updates.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const arcs = reports.flatMap((report) =>
    report.top_source_origins.map((source) => ({
      source: [source.longitude, source.latitude],
      target: [report.longitude, report.latitude],
      posts: source.post_count,
    })),
  );
  return (
    <div className="webgl-map">
      <div ref={host} className="map-base" />
      <DeckGL
        initialViewState={initial}
        controller={true}
        onViewStateChange={({ viewState }) => {
          if ("longitude" in viewState)
            map.current?.jumpTo({
              center: [Number(viewState.longitude), Number(viewState.latitude)],
              zoom: Number(viewState.zoom),
              bearing: Number(viewState.bearing),
              pitch: Number(viewState.pitch),
            });
        }}
        onError={onFailure}
        layers={[
          new PolygonLayer<GeoHexAnomaly>({
            id: "target-cells",
            data: reports,
            getPolygon: (report) =>
              cellToBoundary(report.h3_index).map(([lat, lon]) => [lon, lat]),
            getFillColor: [251, 146, 60, 180],
            getLineColor: [255, 255, 255],
            lineWidthMinPixels: 2,
            stroked: true,
            pickable: true,
            onClick: (info: PickingInfo<GeoHexAnomaly>) => {
              if (info.object) onSelect(info.object.h3_index);
            },
          }),
          new ArcLayer({
            id: "source-arcs",
            data: arcs,
            getSourcePosition: (item) => item.source as [number, number],
            getTargetPosition: (item) => item.target as [number, number],
            getSourceColor: [56, 189, 248],
            getTargetColor: [251, 146, 60],
            getWidth: 2,
          }),
        ]}
      />
      <span className="map-credit">
        Natural Earth land · public domain · local geometry
      </span>
    </div>
  );
}
