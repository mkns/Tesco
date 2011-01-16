#!/usr/bin/perl -w

use strict;
use LWP::UserAgent;
use HTTP::Request::Common;
use Data::Dumper;
use CGI qw( :all );
use strict;

print header();
print start_html(
	'-title' => "Tesco Order",
	'-style' => 'css/style.css'
  ),
  h1("<span id='header'><a href='/Tesco/'>Tesco Orders</a></span>");

my $action = param("action") || 'show_menu';
if ( $action eq 'add_barcode_form' ) {
	show_add_barcode_form();
}
elsif ( $action eq 'add_barcode' ) {
	add_barcode();
}
elsif ( $action eq 'show_categories' ) {
	add_category();
	show_add_category_form();
	show_all_categories();
}
elsif ( $action eq 'show_products' ) {
	show_products();
}
elsif ( $action eq 'show_menu' ) {
	show_menu();
}

print end_html();

sub show_menu {
	print <<EOQ;
<ul>
<li><a href='/Tesco/?action=show_products'>Show Products</a></li>
<li><a href='/Tesco/?action=add_barcode_form'>Add Barcode</a></li>
<li><a href='/Tesco/?action=show_categories'>Show Categories</a></li>
</ul>	
EOQ
}

sub show_products {
	if ( !param("category") ) {
		show_products_categorylist();
	}
	else {
		show_products_form_category();
	}
}

sub show_products_form_category {
	my $category      = param("category");
	my $data          = read_datafile();
	my $category_data = $data->{$category};
	my $columns       = 5;
	print h2($category),
	  p("<a href='/Tesco/?action=add_barcode_form&category=$category'>Add another barcode?</a>"), "\n";
	print "<table cellpadding=10 cellspacing=0 border=1>\n";
	my $counter = scalar(@$category_data) - 1;
	foreach my $i ( 0 .. $counter ) {
		my $item = $category_data->[$i];
		if ( !( $i % $columns ) ) {
			print "<tr valign='top'>\n";
		}
		print "<td>", $item->[1], "<p><img src='barcodes/", $item->[0],
		  ".png' /></p>", "</td>\n";
		if ( !( ( $i + 1 ) % $columns ) || $i eq $counter ) {
			print "</tr>\n";
		}
	}
	print "</table>\n"
}

sub add_category {
	my $category = param("category");
	if ( defined $category && length $category ) {

		# rather than append, we'll read them in to a hash, add the new one
		# and write them back in.  This prevents duplicates being added.
		my %categories = ();
		if ( -e "files/categories.txt" ) {
			open( FILE, "files/categories.txt" );
			%categories = map { $_ => 1 } <FILE>;
			close(FILE);
		}
		$categories{$category} = 1;
		open( FILE, "> files/categories.txt" );
		foreach my $category ( sort keys %categories ) {
			chomp($category);
			print FILE $category, "\n";
		}
		close(FILE);
	}
}

sub show_all_categories {
	open( FILE, "files/categories.txt" );
	my @categories = split( "\n", join( "", <FILE> ) );
	close(FILE);
	print p("Current Categories:");
	print "\n<ul>\n<li>", join( "</li>\n<li>", @categories ), "</li>\n</ul>\n";
}

sub get_list_of_categories {
	open( FILE, "files/categories.txt" );
	my @categories = split( "\n", join( "", <FILE> ) );
	close(FILE);
	return \@categories;
}

sub get_categories_dropdown {
	my $display_category = param("category") || "";
	open( FILE, "files/categories.txt" );
	my @categories = split( "\n", join( "", <FILE> ) );
	close(FILE);
	my $output = "<SELECT name='category'>\n";
	foreach my $category (@categories) {
		$output .= "<OPTION";
		if ( $category eq $display_category ) {
			$output .= " SELECTED ";
		}
		$output .= ">$category</OPTION>\n";
	}
	$output .= "</SELECT>\n";
	return $output;
}

sub show_add_category_form {

	# need to reset the action, otherwise it'll retain the old value
	param( "action", "show_categories" );

	print join( "\n",
		start_form( "POST", "/Tesco/" ),
		p( "Add New Category: ", textfield("category") ),
		p( submit() ),
		hidden( "action", "show_categories" ),
		end_form() );
}

sub add_barcode {
	my $barcode  = param("barcode");
	my $category = param("category");
	my $itemname = param("itemname");
	if ( length($barcode) != 13 && length($barcode) != 8 ) {
		error("Barcode needs to be 8 or 13 digits long");
	}
	if ( length($itemname) < 1 || $itemname !~ /\w/ ) {
		error("Need an item name, you didn't enter one");
	}
	generate_barcode( $barcode, $category, $itemname );
	my $data = read_datafile();
	push @{ $data->{$category} }, [ $barcode, $itemname ];
	write_datafile($data);
	param( "action",   "show_products" );
	param( "category", $category );
	show_products();
}

sub error {
	my ($text) = @_;
	print $text;
	exit 0;
}

sub show_add_barcode_form {

	# need to reset the action, otherwise it'll retain the old value
	param( "action", "add_barcode" );

	print start_form( "POST", "/Tesco/" );
	print "<table cellpadding=3 cellspacing=0 border=1>\n";
	print "<tr><td>Barcode</td><td>",   textfield("barcode"),  "</td></tr>\n";
	print "<tr><td>Item Name</td><td>", textfield("itemname"), "</td></tr>\n";
	print "<tr><td>Category</td><td>", get_categories_dropdown(),
	  "</td></tr>\n";
	print "<tr><td colspan=2>", submit(), "</td></tr>\n";
	print "</table\n";
	print hidden( "action", "add_barcode" ), end_form();
}

sub generate_barcode {
	my ( $barcode, $category, $itemname ) = @_;
	my $ua  = get_ua();
	my $url = "http://www.terryburton.co.uk/barcodewriter/generator/";
	chomp($barcode) if defined($barcode);
	if ( !defined $barcode
		|| ( length($barcode) != 13 && length($barcode) != 8 ) )
	{
		die "Code must be 8 or 13 digits long";
	}
	my $options = "includetext guardwhitespace";
	$options .= " height=0.5" if length($barcode) == 8;
	my $data = [
		data        => $barcode,
		encoder     => "ean" . length($barcode),
		options     => $options,
		rotate      => 0,
		scale_x     => 1,
		scale_y     => 1,
		submit      => "Make Barcode",
		translate_x => 50,
		translate_y => 50,
	];

	my $request = POST $url,
	  Content_Type => 'form-data',
	  Content      => $data;
	my $response = $ua->request($request);
	my @content  = split( "\n", $response->content() );
	my $line     = get_line_of_links_from_content( \@content );
	my $png      = get_png_from_line_of_links($line);
	$request  = GET $url . $png;
	$response = $ua->request($request);
	open( PNG, "> barcodes/$barcode.png" ) or die $!;
	binmode PNG;
	print PNG $response->content();
	close(PNG);
}

sub read_datafile {
	my $categories = get_list_of_categories();
	my %data       = map { $_ => [] } @$categories;
	my $category   = 'Unknown';
	open( FILE, "files/products.txt" );
	while ( my $line = <FILE> ) {
		chomp($line);
		if ( $line !~ /^\d/ ) {
			$category = $line;
		}
		else {
			my ( $barcode, $itemname ) = split( "\t", $line );
			push @{ $data{$category} }, [ $barcode, $itemname ];
		}
	}
	return \%data;
}

sub write_datafile {
	my ($data)     = @_;
	my $categories = get_list_of_categories();
	my $output     = "";
	foreach my $category (@$categories) {
		$output .= "$category\n";
		my $products = $data->{$category};
		foreach my $product (@$products) {
			$output .= join( "\t", @$product ) . "\n";
		}
	}
	open( FILE, "> files/products.txt" );
	print FILE $output;
	close(FILE);
}

sub get_png_from_line_of_links {
	my ($line) = @_;
	my ($png) = $line =~ /"(tmp\/\w+\/barcode\.png)/;
	return $png;
}

sub get_line_of_links_from_content {
	my ($content) = @_;
	foreach my $line (@$content) {
		return $line if $line =~ /Download image as/;
	}
}

sub get_ua {
	my ($cookie_jar) = @_;
	$cookie_jar = '/tmp/cookie_jar' if ( !defined($cookie_jar) );
	my $ua = LWP::UserAgent->new;
	$ua->timeout(10);
	$ua->cookie_jar( { file => $cookie_jar, autosave => 1 } );
	push @{ $ua->requests_redirectable }, 'POST';
	return $ua;
}

sub show_products_categorylist {

	my $categories = get_list_of_categories();
	print "<ul>\n";
	foreach my $category (@$categories) {
		print
"<li><a href=\'/Tesco/?action=show_products&category=$category\'>$category</a></li>\n";
	}
	print "</ul>\n";

	return ($categories);
}
