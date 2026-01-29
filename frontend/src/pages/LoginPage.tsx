import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useAuth } from '../auth/useAuth';
import { login } from '../api/auth';
import toast from 'react-hot-toast';

interface LoginFormData {
  username: string;
  password: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const { dispatch } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>();

  const onSubmit = async (data: LoginFormData) => {
    setIsSubmitting(true);
    try {
      const response = await login(data);
      dispatch({ type: 'LOGIN', payload: response });
      toast.success(`Welcome, ${response.user.username}`);
      navigate('/dashboard', { replace: true });
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { error?: string } } })?.response?.data?.error ||
        'Login failed. Please check your credentials.';
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">EcoClean Dashboard</h1>
          <p className="mt-2 text-sm text-gray-600">Sign in to manage email automation</p>
        </div>

        <div className="card p-6">
          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            <div className="space-y-4">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  className={`input-field ${errors.username ? 'input-error' : ''}`}
                  {...register('username', {
                    required: 'Username is required',
                    maxLength: { value: 100, message: 'Username must be 100 characters or fewer' },
                  })}
                />
                {errors.username && (
                  <p className="mt-1 text-sm text-red-600" role="alert">{errors.username.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  className={`input-field ${errors.password ? 'input-error' : ''}`}
                  {...register('password', {
                    required: 'Password is required',
                  })}
                />
                {errors.password && (
                  <p className="mt-1 text-sm text-red-600" role="alert">{errors.password.message}</p>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary w-full"
              >
                {isSubmitting ? 'Signing in...' : 'Sign in'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
