import { ReactNode, createElement } from 'react';
import { GiCow, GiChicken, GiPig, GiSheep, GiRoastChicken } from 'react-icons/gi';
import {
  GiFishCooked,
  GiShrimp,
  GiCrab,
  GiCrabClaw,
  GiOyster
} from 'react-icons/gi';
import {
  TbAvocado,
  TbCarrot,
  TbPepper,
  TbMushroom
} from 'react-icons/tb';
import {
  GiBroccoli,
  GiCabbage,
  GiLeafSkeleton
} from 'react-icons/gi';
import {
  GiPeanut,
  GiButter,
  GiOlive,
  GiCoconuts
} from 'react-icons/gi';
import {
  GiWaterBottle,
  GiCoffeeCup,
  GiTeapotLeaves,
  GiSodaCan
} from 'react-icons/gi';
import {
  GiMilkCarton
} from 'react-icons/gi';
import {
  IoLeafOutline,
  IoNutritionOutline
} from 'react-icons/io5';
import {
  FaAppleAlt,
  FaBreadSlice,
  FaPizzaSlice,
  FaSeedling
} from 'react-icons/fa';
import {
  GiRiceCooker,
  GiWheat,
  GiBread,
  GiPotato
} from 'react-icons/gi';

// Helper to create icon with className
const icon = (Component: any, className: string): ReactNode =>
  createElement(Component, { className });

export interface FoodItem {
  value: string;
  label: string;
  icon: ReactNode;
}

export interface FoodCategory {
  step: number;
  title: string;
  subtitle?: string;
  items: FoodItem[];
  minItems?: number;
  maxItems?: number;
}

// Step 3: Meat
export const meatItems: FoodItem[] = [
  { value: 'beef', label: 'Beef', icon: icon(GiCow, 'text-red-700') },
  { value: 'lamb', label: 'Lamb', icon: icon(GiSheep, 'text-amber-700') },
  { value: 'chicken', label: 'Chicken', icon: icon(GiChicken, 'text-yellow-600') },
  { value: 'pork', label: 'Pork', icon: icon(GiPig, 'text-pink-600') },
  { value: 'turkey', label: 'Turkey', icon: icon(GiRoastChicken, 'text-orange-700') },
];

// Step 4: Fish & Seafood
export const fishItems: FoodItem[] = [
  { value: 'tuna', label: 'Tuna', icon: icon(GiFishCooked, 'text-blue-600') },
  { value: 'salmon', label: 'Salmon', icon: icon(GiFishCooked, 'text-orange-500') },
  { value: 'mackerel', label: 'Mackerel', icon: icon(GiFishCooked, 'text-blue-700') },
  { value: 'cod', label: 'Cod', icon: icon(GiFishCooked, 'text-gray-600') },
  { value: 'pollock', label: 'Pollock', icon: icon(GiFishCooked, 'text-gray-500') },
];

// Step 5: Low-Carb Vegetables
export const lowCarbVeggieItems: FoodItem[] = [
  { value: 'avocado', label: 'Avocado', icon: icon(TbAvocado, 'text-green-700') },
  { value: 'asparagus', label: 'Asparagus', icon: icon(FaSeedling, 'text-green-600') },
  { value: 'bell_pepper', label: 'Bell Pepper', icon: icon(TbPepper, 'text-red-500') },
  { value: 'zucchini', label: 'Zucchini', icon: icon(TbCarrot, 'text-green-600') },
  { value: 'celery', label: 'Celery', icon: icon(IoLeafOutline, 'text-green-700') },
  { value: 'mushrooms', label: 'Mushrooms', icon: icon(TbMushroom, 'text-amber-800') },
];

// Step 6: Cruciferous Vegetables
export const cruciferousItems: FoodItem[] = [
  { value: 'brussels_sprouts', label: 'Brussels Sprouts', icon: icon(GiCabbage, 'text-green-700') },
  { value: 'kale', label: 'Kale', icon: icon(GiLeafSkeleton, 'text-green-800') },
  { value: 'broccoli', label: 'Broccoli', icon: icon(GiBroccoli, 'text-green-600') },
  { value: 'cauliflower', label: 'Cauliflower', icon: icon(GiBroccoli, 'text-gray-200') },
];

// Step 7: Leafy Greens
export const leafyGreenItems: FoodItem[] = [
  { value: 'lettuce', label: 'Lettuce', icon: icon(IoLeafOutline, 'text-green-500') },
  { value: 'spinach', label: 'Spinach', icon: icon(GiLeafSkeleton, 'text-green-700') },
  { value: 'arugula', label: 'Arugula', icon: icon(IoLeafOutline, 'text-green-600') },
  { value: 'cilantro', label: 'Cilantro', icon: icon(FaSeedling, 'text-green-500') },
  { value: 'iceberg', label: 'Iceberg', icon: icon(IoLeafOutline, 'text-green-400') },
  { value: 'napa_cabbage', label: 'Napa Cabbage', icon: icon(GiCabbage, 'text-green-300') },
];

// Step 8: Legumes (typically avoided on keto, but user preference)
export const legumeItems: FoodItem[] = [
  { value: 'chickpeas', label: 'Chickpeas', icon: icon(IoNutritionOutline, 'text-yellow-700') },
  { value: 'lentils', label: 'Lentils', icon: icon(IoNutritionOutline, 'text-orange-700') },
  { value: 'black_beans', label: 'Black Beans', icon: icon(IoNutritionOutline, 'text-gray-800') },
];

// Step 9: Shellfish
export const shellfishItems: FoodItem[] = [
  { value: 'clams', label: 'Clams', icon: icon(GiOyster, 'text-gray-600') },
  { value: 'shrimp', label: 'Shrimp', icon: icon(GiShrimp, 'text-pink-500') },
  { value: 'crab', label: 'Crab', icon: icon(GiCrab, 'text-red-600') },
  { value: 'lobster', label: 'Lobster', icon: icon(GiCrabClaw, 'text-red-700') },
];

// Step 10: High-Sugar Fruits (to avoid on keto)
export const highSugarFruitItems: FoodItem[] = [
  { value: 'apple', label: 'Apple', icon: icon(FaAppleAlt, 'text-red-500') },
  { value: 'banana', label: 'Banana', icon: icon(GiCoconuts, 'text-yellow-400') },
  { value: 'orange', label: 'Orange', icon: icon(FaAppleAlt, 'text-orange-500') },
  { value: 'berries', label: 'Mixed Berries', icon: icon(FaSeedling, 'text-purple-600') },
];

// Step 11: Low-Sugar Berries
export const lowSugarBerryItems: FoodItem[] = [
  { value: 'strawberries', label: 'Strawberries', icon: icon(FaSeedling, 'text-red-500') },
  { value: 'blueberries', label: 'Blueberries', icon: icon(FaSeedling, 'text-blue-600') },
  { value: 'raspberries', label: 'Raspberries', icon: icon(FaSeedling, 'text-pink-600') },
];

// Step 12: Grains (to avoid on keto)
export const grainItems: FoodItem[] = [
  { value: 'rice', label: 'Rice', icon: icon(GiRiceCooker, 'text-gray-100') },
  { value: 'quinoa', label: 'Quinoa', icon: icon(GiWheat, 'text-yellow-700') },
  { value: 'oats', label: 'Oats', icon: icon(GiWheat, 'text-amber-600') },
];

// Step 13: Starches (to avoid on keto)
export const starchItems: FoodItem[] = [
  { value: 'pasta', label: 'Pasta', icon: icon(FaPizzaSlice, 'text-yellow-600') },
  { value: 'bread', label: 'Bread', icon: icon(FaBreadSlice, 'text-amber-700') },
  { value: 'potatoes', label: 'Potatoes', icon: icon(GiPotato, 'text-yellow-800') },
];

// Step 14: Fats & Oils
export const fatItems: FoodItem[] = [
  { value: 'coconut_oil', label: 'Coconut Oil', icon: icon(GiCoconuts, 'text-white') },
  { value: 'olive_oil', label: 'Olive Oil', icon: icon(GiOlive, 'text-green-700') },
  { value: 'peanut_butter', label: 'Peanut Butter', icon: icon(GiPeanut, 'text-amber-700') },
  { value: 'butter', label: 'Butter', icon: icon(GiButter, 'text-yellow-300') },
  { value: 'lard', label: 'Lard', icon: icon(GiButter, 'text-gray-300') },
];

// Step 15: Beverages
export const beverageItems: FoodItem[] = [
  { value: 'water', label: 'Water', icon: icon(GiWaterBottle, 'text-blue-400') },
  { value: 'coffee', label: 'Coffee', icon: icon(GiCoffeeCup, 'text-amber-900') },
  { value: 'tea', label: 'Tea', icon: icon(GiTeapotLeaves, 'text-green-700') },
  { value: 'soda', label: 'Soda', icon: icon(GiSodaCan, 'text-red-600') },
];

// Step 16: Dairy & Alternatives
export const dairyItems: FoodItem[] = [
  { value: 'greek_yogurt', label: 'Greek Yogurt', icon: icon(GiMilkCarton, 'text-white') },
  { value: 'cheese', label: 'Cheese', icon: icon(GiMilkCarton, 'text-yellow-500') },
  { value: 'sour_cream', label: 'Sour Cream', icon: icon(GiMilkCarton, 'text-gray-100') },
  { value: 'cottage_cheese', label: 'Cottage Cheese', icon: icon(GiMilkCarton, 'text-gray-200') },
];

// Category mapping for all food selection steps
export const foodCategories: FoodCategory[] = [
  {
    step: 3,
    title: 'Select Your Preferred Meats',
    subtitle: 'Choose the meats you enjoy eating',
    items: meatItems,
  },
  {
    step: 4,
    title: 'Select Your Preferred Fish',
    subtitle: 'Choose the fish varieties you like',
    items: fishItems,
  },
  {
    step: 5,
    title: 'Select Low-Carb Vegetables',
    subtitle: 'These are great for keto',
    items: lowCarbVeggieItems,
  },
  {
    step: 6,
    title: 'Select Cruciferous Vegetables',
    subtitle: 'Nutrient-dense keto-friendly options',
    items: cruciferousItems,
  },
  {
    step: 7,
    title: 'Select Leafy Greens',
    subtitle: 'Essential for a healthy keto diet',
    items: leafyGreenItems,
  },
  {
    step: 8,
    title: 'Do You Eat Legumes?',
    subtitle: 'Note: Legumes are high in carbs and typically limited on keto',
    items: legumeItems,
  },
  {
    step: 9,
    title: 'Select Shellfish Preferences',
    subtitle: 'Great protein sources for keto',
    items: shellfishItems,
  },
  {
    step: 10,
    title: 'High-Sugar Fruits',
    subtitle: 'These should be avoided on keto - select any you want to exclude',
    items: highSugarFruitItems,
  },
  {
    step: 11,
    title: 'Low-Sugar Berries',
    subtitle: 'These can be enjoyed in moderation on keto',
    items: lowSugarBerryItems,
  },
  {
    step: 12,
    title: 'Grains',
    subtitle: 'These should be avoided on keto - select any you want to exclude',
    items: grainItems,
  },
  {
    step: 13,
    title: 'Starches',
    subtitle: 'These should be avoided on keto - select any you want to exclude',
    items: starchItems,
  },
  {
    step: 14,
    title: 'Select Your Preferred Fats & Oils',
    subtitle: 'Essential for meeting your fat macros',
    items: fatItems,
  },
  {
    step: 15,
    title: 'Select Your Preferred Beverages',
    subtitle: 'Stay hydrated on your keto journey',
    items: beverageItems,
  },
  {
    step: 16,
    title: 'Select Dairy & Alternatives',
    subtitle: 'Choose your preferred dairy products',
    items: dairyItems,
  },
];

// Helper function to get category by step number
export function getFoodCategoryByStep(step: number): FoodCategory | undefined {
  return foodCategories.find(cat => cat.step === step);
}
