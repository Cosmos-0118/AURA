export type LogoAnchor =
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right'
  | 'center'
  | 'custom';

export interface WatermarkLogo {
  id: string;
  logoPath: string;
  name?: string;
  anchor: LogoAnchor;
  scale: number; // 20–200 (%)
  opacity: number; // 10–100 (%)
  padding?: number;
  x?: number; // 0–100 (%)
  y?: number; // 0–100 (%)
}

export interface LogoConfig {

  x: number; // percent of canvas width (0–100)
  y: number; // percent of canvas height (0–100)
  scale: number; // 20–200 (%)
  opacity: number; // 10–100 (%)
  padding: number; // pixels from edge when using anchor snapping
  anchor: LogoAnchor;
}

export interface TextConfig {
  text: string;
  x: number; // percent of canvas width (0–100)
  y: number; // percent of canvas height (0–100)
  fontSize: number; // 10–72
  color: string; // hex
  bold: boolean;
  italic: boolean;
}
