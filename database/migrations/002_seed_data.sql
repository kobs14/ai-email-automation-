-- =============================================================================
-- Migration: 002_seed_data.sql
-- Description: Seeds the business_config table with initial configuration
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Pricing Rules
-- Base pricing structure by property type
-- -----------------------------------------------------------------------------
INSERT INTO business_config (key, value, description) VALUES
('pricing_rules', '{
    "house": {
        "base": 120,
        "per_bedroom": 25,
        "per_bathroom": 15,
        "minimum": 120
    },
    "apartment": {
        "base": 80,
        "per_bedroom": 20,
        "per_bathroom": 12,
        "minimum": 80
    },
    "condo": {
        "base": 90,
        "per_bedroom": 22,
        "per_bathroom": 13,
        "minimum": 90
    },
    "office": {
        "base": 150,
        "per_sqft": 0.15,
        "minimum": 150
    },
    "studio": {
        "base": 60,
        "flat_rate": true,
        "minimum": 60
    }
}', 'Base pricing by property type. Includes base rate, per-room charges, and minimums.')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description;

-- -----------------------------------------------------------------------------
-- Service Type Multipliers
-- Pricing multipliers for different service types
-- -----------------------------------------------------------------------------
INSERT INTO business_config (key, value, description) VALUES
('service_multipliers', '{
    "standard": {
        "multiplier": 1.0,
        "description": "Regular cleaning service"
    },
    "deep_clean": {
        "multiplier": 1.5,
        "description": "Thorough deep cleaning including baseboards, inside appliances"
    },
    "move_out": {
        "multiplier": 1.8,
        "description": "Complete cleaning for moving out, includes all surfaces"
    },
    "move_in": {
        "multiplier": 1.6,
        "description": "Cleaning before moving into a new space"
    },
    "post_construction": {
        "multiplier": 2.0,
        "description": "Heavy-duty cleaning after construction or renovation"
    },
    "one_time": {
        "multiplier": 1.2,
        "description": "One-time cleaning without recurring service commitment"
    }
}', 'Multipliers applied to base pricing for different service types.')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description;

-- -----------------------------------------------------------------------------
-- Add-on Services
-- Optional additional services with flat fees
-- -----------------------------------------------------------------------------
INSERT INTO business_config (key, value, description) VALUES
('addon_services', '{
    "inside_fridge": {
        "price": 35,
        "description": "Clean inside refrigerator"
    },
    "inside_oven": {
        "price": 40,
        "description": "Clean inside oven"
    },
    "inside_cabinets": {
        "price": 50,
        "description": "Clean inside all cabinets"
    },
    "laundry": {
        "price": 25,
        "description": "Wash, dry, and fold one load of laundry"
    },
    "window_interior": {
        "price": 5,
        "per_unit": true,
        "description": "Clean interior windows (per window)"
    },
    "garage": {
        "price": 75,
        "description": "Sweep and organize garage"
    }
}', 'Optional add-on services with flat fees.')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description;

-- -----------------------------------------------------------------------------
-- Business Information
-- Company contact details and branding
-- -----------------------------------------------------------------------------
INSERT INTO business_config (key, value, description) VALUES
('business_info', '{
    "name": "Sparkle Clean Services",
    "legal_name": "Sparkle Clean Services LLC",
    "email": "info@sparkleclean.com",
    "phone": "(555) 123-4567",
    "website": "www.sparkleclean.com",
    "address": {
        "street": "123 Clean Street",
        "city": "Springfield",
        "state": "IL",
        "zip": "62701"
    },
    "hours": {
        "weekdays": "8:00 AM - 6:00 PM",
        "saturday": "9:00 AM - 4:00 PM",
        "sunday": "Closed"
    },
    "service_area": ["Springfield", "Chatham", "Rochester", "Sherman", "Williamsville"]
}', 'Business contact information and service details.')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description;

-- -----------------------------------------------------------------------------
-- Brand Voice Guidelines
-- Instructions for AI-generated responses
-- -----------------------------------------------------------------------------
INSERT INTO business_config (key, value, description) VALUES
('brand_voice', '{
    "tone": "friendly, professional, helpful, warm",
    "style": "clear and concise, use bullet points for pricing breakdowns, avoid jargon",
    "greeting": "Thank you for reaching out to Sparkle Clean Services!",
    "signature": "Best regards,\nThe Sparkle Clean Team\n\nSparkle Clean Services\n(555) 123-4567\ninfo@sparkleclean.com",
    "guidelines": [
        "Always acknowledge the customer request first",
        "Be specific about pricing when providing quotes",
        "Include next steps or call to action",
        "Offer to answer any questions",
        "Keep responses under 300 words unless detailed info requested"
    ],
    "avoid": [
        "Overly casual language",
        "Making promises about specific times without checking availability",
        "Discussing competitor pricing",
        "Using all caps or excessive punctuation"
    ]
}', 'Guidelines for AI-generated email responses to maintain brand consistency.')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description;

-- -----------------------------------------------------------------------------
-- Response Templates
-- Template structures for different email intents
-- -----------------------------------------------------------------------------
INSERT INTO business_config (key, value, description) VALUES
('response_templates', '{
    "quote_request": {
        "structure": ["greeting", "acknowledgment", "quote_breakdown", "next_steps", "signature"],
        "include_pricing": true,
        "urgency": "respond within 2 hours"
    },
    "booking_request": {
        "structure": ["greeting", "confirmation_pending", "details_summary", "next_steps", "signature"],
        "include_pricing": true,
        "urgency": "respond within 1 hour"
    },
    "rescheduling": {
        "structure": ["greeting", "understanding", "options", "next_steps", "signature"],
        "include_pricing": false,
        "urgency": "respond within 2 hours"
    },
    "complaint": {
        "structure": ["greeting", "empathy", "resolution", "commitment", "signature"],
        "include_pricing": false,
        "urgency": "respond within 30 minutes",
        "escalate": true
    },
    "general_inquiry": {
        "structure": ["greeting", "answer", "additional_info", "next_steps", "signature"],
        "include_pricing": false,
        "urgency": "respond within 4 hours"
    }
}', 'Template structures and guidelines for different email intent types.')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description;

-- -----------------------------------------------------------------------------
-- Entity Extraction Rules
-- Defines what entities to extract for each intent type
-- -----------------------------------------------------------------------------
INSERT INTO business_config (key, value, description) VALUES
('entity_extraction_rules', '{
    "quote_request": [
        "property_type",
        "bedrooms",
        "bathrooms",
        "square_footage",
        "service_type",
        "preferred_date",
        "preferred_time",
        "frequency",
        "special_requests",
        "address",
        "contact_phone"
    ],
    "booking_request": [
        "property_type",
        "bedrooms",
        "bathrooms",
        "service_type",
        "requested_date",
        "requested_time",
        "address",
        "contact_phone",
        "special_instructions"
    ],
    "rescheduling": [
        "original_date",
        "new_preferred_date",
        "new_preferred_time",
        "reason"
    ],
    "complaint": [
        "issue_type",
        "service_date",
        "specific_concerns",
        "desired_resolution"
    ],
    "general_inquiry": [
        "topic",
        "specific_question"
    ]
}', 'Defines which entities to extract based on email intent.')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description;

-- =============================================================================
-- End of Migration: 002_seed_data.sql
-- =============================================================================
