//! layer: command
//! depends-on: parse
//!
//! CLI command execution layer.

use crate::parse;

pub fn run() {
    println!("project-cli ({})", parse::feature_tag());
}
