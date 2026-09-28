export interface Pointer { x: number; y: number }
export interface SceneOptions { lite: boolean; variant?: string }
export interface SceneHandle {
  resize(width: number, height: number, dpr: number): void
  render(time: number, pointer: Pointer): void
  dispose(): void
  /** Time (s) rendered as the single still frame when the user prefers reduced motion. */
  staticTime: number
}
export type SceneFactory = (canvas: HTMLCanvasElement, options: SceneOptions) => SceneHandle
