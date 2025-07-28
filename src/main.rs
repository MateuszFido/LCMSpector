pub mod loading;
pub mod measurements;
pub mod processing;

use std::env;
use std::process;
use std::sync::Arc;
use tokio::runtime;
use futures::future::join_all;
use std::path::Path;
use indicatif::{ProgressBar, ProgressStyle};

fn main() {
    println!(
        "Running LCMSpector backend version {}",
        env!("CARGO_PKG_VERSION")
    );
    let args: Vec<String> = env::args().collect();

    // Require 3 arguments: program name, ion list name, and file list path
    if args.len() != 3 {
        eprintln!("Usage: {} <ion_list_name> <file_list_path>", args[0]);
        process::exit(1);
    }

    let ion_list_name = &args[1];
    let file_list_path = &args[2];

    // Read file paths from the specified file
    let file_paths = match loading::read_file_paths(file_list_path) {
        Ok(paths) => paths,
        Err(e) => {
            eprintln!("Error reading file list: {}", e);
            process::exit(1);
        }
    };
    
    println!("Processing {} files with ion list: {}", file_paths.len(), ion_list_name);
    
    // Create a multi-threaded runtime for async IO operations
    let rt = runtime::Builder::new_multi_thread()
        .worker_threads(4) // Optimized for IO-bound operations
        .enable_all()
        .build()
        .expect("Failed to create Tokio runtime");
    
    rt.block_on(async {
        if file_paths.len() > 25 {
            // For large batches, use hybrid approach (Tokio + Rayon)
            process_large_batch(&file_paths, ion_list_name, 0.0001).await
        } else {
            // For smaller batches, use standard Rayon approach
            let results = loading::process_files_in_parallel(&file_paths, ion_list_name, 0.0001);
            println!("Processed {} files using standard parallel approach", results.len());
        }
    });
    
    process::exit(0);
}

async fn process_large_batch(
    file_paths: &[String],
    ion_list_name: &str,
    mass_accuracy: f64,
) {
    let start = std::time::Instant::now();
    println!("Starting optimized large-batch processing for {} files...", file_paths.len());
    
    // Load ion list once and share it across all tasks
    let ion_list = Arc::new(loading::load_ion_lists(ion_list_name));
    
    // Determine optimal batch size based on available cores
    let num_physical_cores = num_cpus::get_physical();
    let batch_size = std::cmp::max(5, file_paths.len() / (num_physical_cores * 2));
    println!("Splitting into batches of approximately {} files each", batch_size);
    
    // Create a progress bar for overall progress
    let progress_bar = ProgressBar::new(file_paths.len() as u64);
    progress_bar.set_style(
        ProgressStyle::default_bar()
            .template("[{elapsed_precise}] {wide_bar:.cyan/blue} {pos}/{len} files ({percent}%, ETA: {eta})")
            .expect("Failed to create progress style")
    );
    
    // Split files into batches for processing
    let batches: Vec<Vec<String>> = file_paths
        .chunks(batch_size)
        .map(|chunk| chunk.to_vec())
        .collect();
    
    // Create shared progress bar
    let progress_bar = Arc::new(progress_bar);
    
    // Process each batch asynchronously
    let batch_futures = batches.into_iter().map(|batch| {
        let ion_list_clone = Arc::clone(&ion_list);
        let progress_bar_clone = Arc::clone(&progress_bar);
        
        tokio::spawn(async move {
            // Process this batch of files
            process_file_batch(batch, ion_list_clone, mass_accuracy, progress_bar_clone).await
        })
    });
    
    // Wait for all batches to complete
    let batch_results = join_all(batch_futures).await;
    
    // Count total processed files
    let total_processed = batch_results.iter()
        .filter_map(|r| r.as_ref().ok())
        .map(|v| v.len())
        .sum::<usize>();
    
    progress_bar.finish_with_message(format!("Processed {} files in {:.2?}", 
        total_processed, start.elapsed()));
    
    println!("Large-batch processing completed in {:.2?} seconds", start.elapsed());
}

/// Process a batch of files asynchronously
///
/// This function handles a smaller subset of files within the large batch processing
async fn process_file_batch(
    batch: Vec<String>,
    ion_list: Arc<Vec<measurements::Compound>>,
    mass_accuracy: f64,
    progress_bar: Arc<ProgressBar>
) -> Vec<(String, Vec<measurements::Compound>)> {
    let mut results = Vec::with_capacity(batch.len());
    
    for file_path in batch {
        // File operations could be made async for further optimization
        // But keeping synchronous for compatibility with existing code
    let _file_name = Path::new(&file_path).file_name()
        .map(|f| f.to_string_lossy().to_string())
        .unwrap_or_else(|| file_path.clone());
        
        // Process the file
        let (ms1_scans, _) = loading::load_ms_scans(&file_path);
        let compounds = processing::construct_xics(&ms1_scans, &ion_list, mass_accuracy);
        
        // Store the result
        results.push((file_path, compounds));
        
        // Update progress
        progress_bar.inc(1);
    }
    
    results
}
