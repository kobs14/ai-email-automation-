export type ConfigKey =
  | 'pricing_rules'
  | 'service_multipliers'
  | 'addon_services'
  | 'business_info'
  | 'brand_voice'
  | 'response_templates'
  | 'entity_extraction_rules';

export type ConfigValue = Record<string, unknown>;

export interface ConfigEntry {
  key: string;
  value: ConfigValue;
  description?: string;
  updated_at?: string;
}
