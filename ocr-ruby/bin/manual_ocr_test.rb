#!/usr/bin/env ruby
# -*- coding: utf-8 -*-

require_relative '../lib/ocr_processor'

# 手動で画像パスを指定してOCR処理をテスト
image_paths = [
  'C:\Users\yuuji\Sanyuu2Kouku\cursor_tools\summarygenerator\ocr-ruby\test_images\RIMG8575.JPG',
  'C:\Users\yuuji\Sanyuu2Kouku\cursor_tools\summarygenerator\ocr-ruby\test_images\RIMG8576.JPG',
  'C:\Users\yuuji\Sanyuu2Kouku\cursor_tools\summarygenerator\ocr-ruby\test_images\RIMG8577.JPG'
]

puts "=== 手動画像パス指定OCRテスト ==="

# 存在する画像のみフィルタ
existing_images = image_paths.select { |path| File.exist?(path) }
puts "存在する画像: #{existing_images.size}件"

if existing_images.empty?
  puts "テスト用画像が見つかりません"
  exit 1
end

# OCR処理実行
processor = OCRProcessor.new(time_window: 300)
results = processor.process_images(existing_images)

# 結果出力
puts "\n=== 処理結果 ==="
results.each_with_index do |result, i|
  puts "#{i + 1}. #{File.basename(result.image_path)}"
  puts "   Survey Point: #{result.formatted_survey_point || '（不明）'}"
  puts "   補完: #{result.supplemented? ? '有り' : '無し'}"
  puts "   OCRテキスト: #{result.location_value || '未検出'}"
end

puts "\n統計:"
puts "処理済み: #{results.size}件"
puts "補完済み: #{results.count(&:supplemented?)}件"
