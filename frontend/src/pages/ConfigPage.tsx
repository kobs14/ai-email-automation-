import { useAllConfig, useUpdateConfig } from '../hooks/useConfig';
import { PricingEditor } from '../components/config/PricingEditor';
import { BrandVoiceEditor } from '../components/config/BrandVoiceEditor';
import { TemplateEditor } from '../components/config/TemplateEditor';
import { BusinessInfoEditor } from '../components/config/BusinessInfoEditor';
import { PageLoader } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';

export function ConfigPage() {
  const { data, isLoading, error, refetch } = useAllConfig();
  const updateMutation = useUpdateConfig();

  if (isLoading) return <PageLoader />;
  if (error) return <ErrorAlert message="Failed to load configuration" onRetry={refetch} />;

  const config = data?.items ?? {};

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="card p-6">
        <BusinessInfoEditor
          data={config['business_info'] ?? {}}
          onSave={(value) => updateMutation.mutate({ key: 'business_info', value })}
          isSaving={updateMutation.isPending}
        />
      </div>

      <div className="card p-6">
        <PricingEditor
          data={config['pricing_rules'] ?? {}}
          onSave={(value) => updateMutation.mutate({ key: 'pricing_rules', value })}
          isSaving={updateMutation.isPending}
        />
      </div>

      <div className="card p-6">
        <BrandVoiceEditor
          data={config['brand_voice'] ?? {}}
          onSave={(value) => updateMutation.mutate({ key: 'brand_voice', value })}
          isSaving={updateMutation.isPending}
        />
      </div>

      <div className="card p-6">
        <TemplateEditor
          data={config['response_templates'] ?? {}}
          onSave={(value) => updateMutation.mutate({ key: 'response_templates', value })}
          isSaving={updateMutation.isPending}
        />
      </div>
    </div>
  );
}
