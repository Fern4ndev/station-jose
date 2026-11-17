export interface ApiErrorEnvelope {
  readonly success: false;
  readonly error: {
    readonly code: string;
    readonly message: string;
    readonly details: Readonly<Record<string, unknown>>;
  };
}
