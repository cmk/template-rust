#![forbid(unsafe_code)]

mod command;
mod parse;

fn main() {
    command::run();
}
