define( function() {

    window.sd = window.sd || {};

    if( window.sd.json === undefined )
        window.sd.json = JSON.parse( window.server_data || '{}' );

    if( window.sd.get === undefined ) {
        window.sd.get = function( path, def_value ) {
            var links = !path ? [] : path.split( '.' );
            var data = window.sd.json;
            for( var ii = 0; ii < links.length; ++ii ) {
	        if( !data || !data.hasOwnProperty( links[ii] ) )
	            return def_value;
	        data = data[links[ii]];
            }
            return data;
        }
    }

    return window.sd;
});
