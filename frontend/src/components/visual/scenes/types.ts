/** Cursor relative to the scene box (−1…1 inside it, up to ±1.6 around it) and how present it is (0…1, eased). */
export interface Pointer { x: number; y: number; active: number }
export interface SceneOptions { lite: boolean; variant?: string }
export interface SceneHandle {
  resize(width: number, height: number, dpr: number): void
  render(time: number, pointer: Pointer): void
  dispose(): void
  /** Time (s) rendered as the single still frame when the user prefers reduced motion. */
  staticTime: number
}
export type SceneFactory = (canvas: HTMLCanvasElement, options: SceneOptions) => SceneHandle
