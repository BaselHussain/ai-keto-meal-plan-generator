import { z } from 'zod';

/**
 * Zod validation schemas for all 20 quiz steps
 * Following frontend-quiz-engineer.md guidelines with clear error messages
 */

// Step 1: Gender Selection
export const step1Schema = z.object({
  step_1: z.enum(['male', 'female'], {
    message: 'Please select your gender to calculate your calorie needs',
  }),
});

// Step 2: Activity Level
export const step2Schema = z.object({
  step_2: z.enum(
    ['sedentary', 'lightly_active', 'moderately_active', 'very_active', 'super_active'],
    {
      message: 'Please select your activity level',
    }
  ),
});

// Steps 3-16: Food Selections
// Reusable food array schema
const foodArraySchema = z.array(z.string()).default([]);

export const step3Schema = z.object({
  step_3: foodArraySchema, // Poultry
});

export const step4Schema = z.object({
  step_4: foodArraySchema, // Fish & Seafood
});

export const step5Schema = z.object({
  step_5: foodArraySchema, // Low-Carb Vegetables
});

export const step6Schema = z.object({
  step_6: foodArraySchema, // Cruciferous Vegetables
});

export const step7Schema = z.object({
  step_7: foodArraySchema, // Leafy Greens
});

export const step8Schema = z.object({
  step_8: foodArraySchema, // Additional Vegetables
});

export const step9Schema = z.object({
  step_9: foodArraySchema, // Additional Proteins
});

export const step10Schema = z.object({
  step_10: foodArraySchema, // Organ Meats
});

export const step11Schema = z.object({
  step_11: foodArraySchema, // Berries (limited)
});

export const step12Schema = z.object({
  step_12: foodArraySchema, // Nuts & Seeds
});

export const step13Schema = z.object({
  step_13: foodArraySchema, // Herbs & Spices
});

export const step14Schema = z.object({
  step_14: foodArraySchema, // Fats & Oils
});

export const step15Schema = z.object({
  step_15: foodArraySchema, // Beverages
});

export const step16Schema = z.object({
  step_16: foodArraySchema, // Dairy & Alternatives
});

// Step 17: Dietary Restrictions (FR-Q-004)
export const step17Schema = z.object({
  step_17: z
    .string()
    .max(500, 'Dietary restrictions must be 500 characters or less')
    .default('')
    .refine(
      (val) => {
        // Warn if user includes medical terms (soft validation)
        const medicalTerms = [
          'diabetes',
          'disease',
          'condition',
          'diagnosis',
          'disorder',
          'syndrome',
        ];
        const lower = val.toLowerCase();
        return !medicalTerms.some((term) => lower.includes(term));
      },
      {
        message:
          'Please avoid including medical diagnoses. Focus only on food preferences and allergies.',
      }
    ),
});

// Step 18: Meals Per Day
export const step18Schema = z.object({
  step_18: z.enum(['2_meals', '3_meals', '4_meals'], {
    message: 'Please select meals per day',
  }),
});

// Step 19: Personal Traits (FR-Q-005)
export const step19Schema = z.object({
  step_19: z
    .array(
      z.enum([
        'tired_waking_up',
        'frequent_cravings',
        'prefer_salty',
        'prefer_sweet',
        'struggle_appetite_control',
      ])
    )
    .default([]),
});

// Step 20: Biometrics (FR-Q-019)
export const step20Schema = z.object({
  step_20: z
    .object({
      age: z
        .number({
          message: 'Age must be a valid number',
        })
        .int('Age must be a whole number')
        .min(18, 'You must be at least 18 years old')
        .max(100, 'Age must be 100 or less'),
      weight_kg: z
        .number({
          message: 'Weight must be a valid number',
        })
        .min(30, 'Weight must be at least 30 kg (66 lbs)')
        .max(300, 'Weight must be 300 kg (661 lbs) or less'),
      height_cm: z
        .number({
          message: 'Height must be a valid number',
        })
        .min(122, 'Height must be at least 122 cm (4\'0")')
        .max(229, 'Height must be 229 cm (7\'6") or less'),
      goal: z.enum(['weight_loss', 'maintenance', 'muscle_gain'], {
        message: 'Please select your fitness goal',
      }),
    })
    .refine(
      (data) => {
        // Validate reasonable BMI range (soft warning, not blocking)
        if (data.weight_kg > 0 && data.height_cm > 0) {
          const heightM = data.height_cm / 100;
          const bmi = data.weight_kg / (heightM * heightM);
          return bmi >= 12 && bmi <= 60; // Very permissive range
        }
        return true;
      },
      {
        message:
          'The height and weight combination seems unusual. Please double-check your entries.',
      }
    ),
});

// Complete quiz validation schema
export const completeQuizSchema = z
  .object({
    step_1: step1Schema.shape.step_1,
    step_2: step2Schema.shape.step_2,
    step_3: step3Schema.shape.step_3,
    step_4: step4Schema.shape.step_4,
    step_5: step5Schema.shape.step_5,
    step_6: step6Schema.shape.step_6,
    step_7: step7Schema.shape.step_7,
    step_8: step8Schema.shape.step_8,
    step_9: step9Schema.shape.step_9,
    step_10: step10Schema.shape.step_10,
    step_11: step11Schema.shape.step_11,
    step_12: step12Schema.shape.step_12,
    step_13: step13Schema.shape.step_13,
    step_14: step14Schema.shape.step_14,
    step_15: step15Schema.shape.step_15,
    step_16: step16Schema.shape.step_16,
    step_17: step17Schema.shape.step_17,
    step_18: step18Schema.shape.step_18,
    step_19: step19Schema.shape.step_19,
    step_20: step20Schema.shape.step_20,
  })
  .refine(
    (data) => {
      // FR-Q-017: Total food items validation (10-item minimum)
      const totalFoodItems = [
        ...data.step_3,
        ...data.step_4,
        ...data.step_5,
        ...data.step_6,
        ...data.step_7,
        ...data.step_8,
        ...data.step_9,
        ...data.step_10,
        ...data.step_11,
        ...data.step_12,
        ...data.step_13,
        ...data.step_14,
        ...data.step_15,
        ...data.step_16,
      ].length;

      return totalFoodItems >= 10;
    },
    {
      message:
        'Please select at least 10 food items across all categories to ensure meal plan variety. Currently selected: {count} items.',
      path: ['foodItems'],
    }
  );

// Type exports for TypeScript
export type Step1Data = z.infer<typeof step1Schema>;
export type Step2Data = z.infer<typeof step2Schema>;
export type Step17Data = z.infer<typeof step17Schema>;
export type Step18Data = z.infer<typeof step18Schema>;
export type Step19Data = z.infer<typeof step19Schema>;
export type Step20Data = z.infer<typeof step20Schema>;
export type CompleteQuizData = z.infer<typeof completeQuizSchema>;

/**
 * Validation helper functions
 */

// Get total food items count across all food steps
export function getTotalFoodItemsCount(quizData: Partial<CompleteQuizData>): number {
  const foodSteps = [
    quizData.step_3 || [],
    quizData.step_4 || [],
    quizData.step_5 || [],
    quizData.step_6 || [],
    quizData.step_7 || [],
    quizData.step_8 || [],
    quizData.step_9 || [],
    quizData.step_10 || [],
    quizData.step_11 || [],
    quizData.step_12 || [],
    quizData.step_13 || [],
    quizData.step_14 || [],
    quizData.step_15 || [],
    quizData.step_16 || [],
  ];

  return foodSteps.flat().length;
}

// Check if warning should be shown (FR-Q-017: 10-14 items)
export function shouldShowFoodItemWarning(count: number): boolean {
  return count >= 10 && count <= 14;
}

// Check if blocking error should be shown (FR-Q-017: <10 items)
export function hasFoodItemError(count: number): boolean {
  return count < 10;
}

// Validate specific step
export function validateStep(stepNumber: number, data: any): { success: boolean; error?: string } {
  try {
    const schemas = [
      step1Schema,
      step2Schema,
      step3Schema,
      step4Schema,
      step5Schema,
      step6Schema,
      step7Schema,
      step8Schema,
      step9Schema,
      step10Schema,
      step11Schema,
      step12Schema,
      step13Schema,
      step14Schema,
      step15Schema,
      step16Schema,
      step17Schema,
      step18Schema,
      step19Schema,
      step20Schema,
    ];

    const schema = schemas[stepNumber - 1];
    if (!schema) {
      return { success: false, error: 'Invalid step number' };
    }

    schema.parse(data);
    return { success: true };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { success: false, error: error.issues[0]?.message || 'Validation failed' };
    }
    return { success: false, error: 'Validation failed' };
  }
}
