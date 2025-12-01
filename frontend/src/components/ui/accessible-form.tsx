/**
 * 可访问的表单组件
 * 提供增强的ARIA支持、验证和错误处理的表单组件
 */

import React, { useState, useCallback, useRef, useEffect, ReactNode } from 'react';
import { createAriaProps, ARIA_PATTERNS } from '@/utils/accessibility/aria-utils';
import { Button } from './button';
import { Card, CardContent, CardHeader, CardTitle } from './card';
import { ScreenReaderAnnouncer } from './screen-reader-announcer';

export interface AccessibleFieldProps {
  /** 字段ID */
  id: string;
  /** 字段标签 */
  label: string;
  /** 字段描述 */
  description?: string;
  /** 是否必填 */
  required?: boolean;
  /** 是否有错误 */
  error?: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 字段类型 */
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  /** 输入值 */
  value?: string;
  /** 占位符 */
  placeholder?: string;
  /** 自动完成 */
  autoComplete?: string;
  /** 输入模式 */
  inputMode?: 'none' | 'text' | 'decimal' | 'numeric' | 'tel' | 'search' | 'email' | 'url';
  /** 最小长度 */
  minLength?: number;
  /** 最大长度 */
  maxLength?: number;
  /** 最小值（数字类型） */
  min?: number | string;
  /** 最大值（数字类型） */
  max?: number | string;
  /** 步长（数字类型） */
  step?: number | string;
  /** 变化回调 */
  onChange?: (value: string) => void;
  /** 焦点回调 */
  onFocus?: () => void;
  /** 失焦回调 */
  onBlur?: () => void;
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 可访问的输入字段组件
 */
export const AccessibleField: React.FC<AccessibleFieldProps> = ({
  id,
  label,
  description,
  required = false,
  error,
  disabled = false,
  type = 'text',
  value,
  placeholder,
  autoComplete,
  inputMode,
  minLength,
  maxLength,
  min,
  max,
  step,
  onChange,
  onFocus,
  onBlur,
  className = '',
}) => {
  const [fieldError, setFieldError] = useState(error);
  const [hasBeenBlurred, setHasBeenBlurred] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // 更新错误状态
  useEffect(() => {
    setFieldError(error);
  }, [error]);

  // 处理输入变化
  const handleChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    if (onChange) {
      onChange(newValue);
    }

    // 实时验证（仅在已经失焦后）
    if (hasBeenBlurred) {
      validateField(newValue);
    }
  }, [onChange, hasBeenBlurred]);

  // 处理失焦
  const handleBlur = useCallback((event: React.FocusEvent<HTMLInputElement>) => {
    setHasBeenBlurred(true);
    const newValue = event.target.value;
    validateField(newValue);
    if (onBlur) {
      onBlur();
    }
  }, [onBlur]);

  // 字段验证
  const validateField = useCallback((value: string) => {
    const errors = [];

    // 必填验证
    if (required && !value.trim()) {
      errors.push(`${label}是必填的`);
    }

    // 长度验证
    if (minLength && value.length < minLength) {
      errors.push(`${label}最少需要${minLength}个字符`);
    }

    if (maxLength && value.length > maxLength) {
      errors.push(`${label}不能超过${maxLength}个字符`);
    }

    // 类型验证
    if (type === 'email' && value && !isValidEmail(value)) {
      errors.push('请输入有效的邮箱地址');
    }

    if (type === 'number' && value && !isValidNumber(value, min, max)) {
      errors.push('请输入有效的数字');
    }

    // URL验证
    if (type === 'url' && value && !isValidUrl(value)) {
      errors.push('请输入有效的URL');
    }

    const errorMessage = errors.length > 0 ? errors[0] : undefined;
    setFieldError(errorMessage);

    return errorMessage;
  }, [required, label, type, minLength, maxLength, min, max]);

  // 生成辅助ID
  const descriptionId = description ? `${id}-description` : undefined;
  const errorId = fieldError ? `${id}-error` : undefined;

  // 构建ARIA属性
  const ariaProps = createAriaProps()
    .labelledBy(`${id}-label`)
    .describedBy([descriptionId, errorId].filter(Boolean).join(' '))
    .required(required)
    .invalid(!!fieldError)
    .disabled(disabled);

  return (
    <div className={`accessible-field ${className}`}>
      {/* 标签 */}
      <label
        id={`${id}-label`}
        htmlFor={id}
        className="block text-sm font-medium mb-1"
      >
        {label}
        {required && <span className="text-red-500 ml-1" aria-label="必填">*</span>}
      </label>

      {/* 描述 */}
      {description && (
        <div id={descriptionId} className="text-sm text-muted-foreground mb-2">
          {description}
        </div>
      )}

      {/* 输入字段 */}
      <div className="relative">
        <input
          ref={inputRef}
          id={id}
          type={type}
          value={value}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete={autoComplete}
          inputMode={inputMode}
          minLength={minLength}
          maxLength={maxLength}
          min={min}
          max={max}
          step={step}
          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            fieldError
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:border-blue-500'
          } ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'}`}
          onChange={handleChange}
          onBlur={handleBlur}
          onFocus={onFocus}
          aria-invalid={!!fieldError}
          aria-required={required}
          aria-describedby={ariaProps.build()['aria-describedby']}
          {...ariaProps.build()}
        />
      </div>

      {/* 错误消息 */}
      {fieldError && (
        <div
          id={errorId}
          role="alert"
          aria-live="polite"
          className="mt-1 text-sm text-red-600"
        >
          {fieldError}
        </div>
      )}
    </div>
  );
};

export interface AccessibleSelectProps {
  /** 选择框ID */
  id: string;
  /** 选择框标签 */
  label: string;
  /** 选项列表 */
  options: Array<{
    value: string;
    label: string;
    disabled?: boolean;
  }>;
  /** 选中的值 */
  value?: string;
  /** 是否必填 */
  required?: boolean;
  /** 是否禁用 */
  disabled?: boolean;
  /** 错误消息 */
  error?: string;
  /** 占位符 */
  placeholder?: string;
  /** 是否多选 */
  multiple?: boolean;
  /** 变化回调 */
  onChange?: (value: string | string[]) => void;
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 可访问的选择框组件
 */
export const AccessibleSelect: React.FC<AccessibleSelectProps> = ({
  id,
  label,
  options,
  value,
  required = false,
  disabled = false,
  error,
  placeholder,
  multiple = false,
  onChange,
  className = '',
}) => {
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [errorId].filter(Boolean).join(' ');

  return (
    <div className={`accessible-select ${className}`}>
      <label
        htmlFor={id}
        className="block text-sm font-medium mb-1"
      >
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>

      <select
        id={id}
        value={value}
        disabled={disabled}
        multiple={multiple}
        required={required}
        className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          error
            ? 'border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:border-blue-500'
        } ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'}`}
        onChange={(e) => {
          if (multiple) {
            const selectedValues = Array.from(e.target.selectedOptions, option => option.value);
            onChange?.(selectedValues);
          } else {
            onChange?.(e.target.value);
          }
        }}
        aria-invalid={!!error}
        aria-required={required}
        aria-describedby={describedBy}
        {...createAriaProps().label(label).required(required).disabled(disabled).build()}
      >
        {placeholder && !multiple && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
            disabled={option.disabled}
          >
            {option.label}
          </option>
        ))}
      </select>

      {error && (
        <div
          id={errorId}
          role="alert"
          aria-live="polite"
          className="mt-1 text-sm text-red-600"
        >
          {error}
        </div>
      )}
    </div>
  );
};

export interface AccessibleFormProps {
  /** 表单标题 */
  title: string;
  /** 表单描述 */
  description?: string;
  /** 提交按钮文本 */
  submitText?: string;
  /** 取消按钮文本 */
  cancelText?: string;
  /** 是否正在提交 */
  isSubmitting?: boolean;
  /** 表单内容 */
  children: ReactNode;
  /** 提交回调 */
  onSubmit?: (event: React.FormEvent) => void;
  /** 取消回调 */
  onCancel?: () => void;
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 可访问的表单组件
 */
export const AccessibleForm: React.FC<AccessibleFormProps> = ({
  title,
  description,
  submitText = '提交',
  cancelText = '取消',
  isSubmitting = false,
  children,
  onSubmit,
  onCancel,
  className = '',
}) => {
  const [announcement, setAnnouncement] = useState<string>('');

  const handleSubmit = useCallback((event: React.FormEvent) => {
    event.preventDefault();
    setAnnouncement('表单正在提交，请稍候...');
    onSubmit?.(event);
  }, [onSubmit]);

  const handleCancel = useCallback(() => {
    setAnnouncement('表单操作已取消');
    onCancel?.();
  }, [onCancel]);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && (
          <p className="text-muted-foreground">{description}</p>
        )}
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} noValidate>
          {children}

          {/* 表单按钮 */}
          <div className="flex items-center space-x-4 mt-6">
            <Button
              type="submit"
              disabled={isSubmitting}
              aria-busy={isSubmitting}
              aria-describedby={isSubmitting ? 'submit-status' : undefined}
            >
              {isSubmitting ? '提交中...' : submitText}
            </Button>

            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
                disabled={isSubmitting}
              >
                {cancelText}
              </Button>
            )}

            {isSubmitting && (
              <div
                id="submit-status"
                className="text-sm text-muted-foreground"
                aria-live="polite"
              >
                正在处理您的请求，请稍候...
              </div>
            )}
          </div>
        </form>
      </CardContent>

      {/* 屏幕阅读器通知 */}
      <ScreenReaderAnnouncer
        message={announcement}
        politeness="polite"
      />
    </Card>
  );
};

// 工具函数
const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

const isValidNumber = (value: string, min?: number | string, max?: number | string): boolean => {
  const num = parseFloat(value);
  if (isNaN(num)) return false;
  if (min !== undefined && num < parseFloat(min.toString())) return false;
  if (max !== undefined && num > parseFloat(max.toString())) return false;
  return true;
};

const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

export default AccessibleForm;