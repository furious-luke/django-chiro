define(
    [ 'jquery', 'bloodhound', 'typeahead' ],
    function( $ ) {

	var typeahead = function( selector, url ) {
	    var products = new Bloodhound({
		datumTokenizer: Bloodhound.tokenizers.obj.whitespace( 'value' ),
		queryTokenizer: Bloodhound.tokenizers.whitespace,
		remote: {
		    url: url + '?q=%QUERY',
		    wildcard: '%QUERY',
		    transform: function( response ) {
			return response.objects;
		    }
		}
	    });

	    var el = $( selector );
	    el.typeahead( null, {
		name: 'products',
		display: function( obj ) {
		    return obj.name;
		},
		source: products
	    });

	    return el;
	}

	return typeahead;
    }
);
