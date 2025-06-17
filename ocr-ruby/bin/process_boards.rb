#!/usr/bin/env ruby
# -*- coding: utf-8 -*-

require_relative '../lib/ocr_processor'
require 'optparse'
require 'json'

# OCRボード処理のメインスクリプト
class ProcessBoardsApp
  def initialize
    @options = parse_options
  end
  
  def run
    puts "=== OCR Caption Board Processor (Ruby) ==="
    
    # 設定確認
    validate_config
    
    # 画像ファイル収集
    image_paths = collect_image_paths(@options[:input])
    
    if image_paths.empty?
      puts "エラー: 処理対象の画像が見つかりません"
      exit 1
    end
    
    # OCR処理実行
    processor = OCRProcessor.new(
      config_path: @options[:config],
      time_window: @options[:time_window]
    )
    
    results = processor.process_images(image_paths)
    
    # 結果出力
    output_results(results)
    
    puts "\n=== 処理完了 ==="
    puts "処理済み: #{results.size}件"
    puts "補完済み: #{results.count(&:supplemented?)}件"
  end
  
  private
  
  def parse_options
    options = {
      input: nil,
      output: nil,
      config: File.join(__dir__, '../config/document_ai.json'),
      time_window: 300
    }
    
    parser = OptionParser.new do |opts|
      opts.banner = "使用方法: #{$0} [オプション]"
      
      opts.on('-i', '--input DIR', '入力ディレクトリ（画像ファイルを含む）') do |dir|
        options[:input] = dir
      end
      
      opts.on('-o', '--output FILE', '出力ファイル（JSON形式）') do |file|
        options[:output] = file
      end
      
      opts.on('-c', '--config FILE', 'DocumentAI設定ファイル') do |file|
        options[:config] = file
      end
      
      opts.on('-t', '--time-window SECONDS', Integer, 'Survey Point補完の時刻窓（秒）') do |seconds|
        options[:time_window] = seconds
      end
      
      opts.on('-h', '--help', 'ヘルプを表示') do
        puts opts
        exit
      end
    end
    
    parser.parse!
    
    # 必須オプションチェック
    unless options[:input]
      puts "エラー: 入力ディレクトリを指定してください (-i オプション)"
      puts parser
      exit 1
    end
    
    options
  end
  
  def validate_config
    config_path = @options[:config]
    
    unless File.exist?(config_path)
      puts "警告: DocumentAI設定ファイルが見つかりません: #{config_path}"
      puts "デモモードで実行します（OCR結果はダミーデータ）"
      return
    end
    
    begin
      config = JSON.parse(File.read(config_path))
      required_keys = ['project_id', 'location', 'processor_id']
      
      missing_keys = required_keys - config.keys
      unless missing_keys.empty?
        puts "エラー: 設定ファイルに必須項目が不足しています: #{missing_keys.join(', ')}"
        exit 1
      end
      
      puts "DocumentAI設定: プロジェクト=#{config['project_id']}, 場所=#{config['location']}"
    rescue JSON::ParserError => e
      puts "エラー: 設定ファイルのJSON形式が無効です: #{e.message}"
      exit 1
    end
  end
    def collect_image_paths(input_dir)
    unless Dir.exist?(input_dir)
      puts "エラー: 入力ディレクトリが存在しません: #{input_dir}"
      exit 1
    end
      # サポートする画像形式（大文字・小文字両方）
    extensions = %w[*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.JPG *.JPEG *.PNG *.BMP *.TIFF *.TIF]
    image_paths = []
    
    puts "画像検索中: #{input_dir}"
      extensions.each do |ext|
      pattern = File.join(input_dir, ext)
      matches = Dir.glob(pattern, File::FNM_CASEFOLD)
      puts "パターン #{ext}: #{matches.size}件"
      image_paths.concat(matches)
    end
    
    puts "検出された画像: #{image_paths.size}件"
    image_paths.each { |path| puts "  #{File.basename(path)}" }
    
    image_paths.sort
  end
  
  def output_results(results)
    output_file = @options[:output]
    
    if output_file
      # JSON形式で出力
      File.write(output_file, JSON.pretty_generate(results.map(&:to_h)))
      puts "結果をファイルに出力しました: #{output_file}"
    else
      # コンソールに概要表示
      puts "\n=== 処理結果サマリー ==="
      results.each_with_index do |result, i|
        puts "#{i + 1}. #{File.basename(result.image_path)}"
        puts "   Survey Point: #{result.formatted_survey_point || '（不明）'}"
        puts "   補完: #{result.supplemented? ? '有り' : '無し'}"
      end
    end
  end
end

# スクリプト実行
if __FILE__ == $0
  begin
    app = ProcessBoardsApp.new
    app.run
  rescue Interrupt
    puts "\n処理が中断されました"
    exit 1
  rescue => e
    puts "エラー: #{e.message}"
    puts e.backtrace if ENV['DEBUG']
    exit 1
  end
end
